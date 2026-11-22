"""Resume read operations by upstream ID. A paid start is never retried."""

import argparse
import logging
import os
import time
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .. import core, journeys
from ..contextqa import recorded_run
from ..loop import fingerprint
from .captures import capture_client, check_target, private_root, source_config


def update(db, job, state, reason=None, run=None, receipt=None):
    db.execute(
        """UPDATE docs_capture_jobs SET status=%s,reason=%s,provider_run=COALESCE(%s,provider_run),
        receipt=COALESCE(%s,receipt),next_at=now()+interval '12 seconds',attempts=attempts+1 WHERE id=%s""",
        (state, reason, run, Jsonb(receipt) if receipt is not None else None, job),
    )
    db.commit()


def advance(db, row):
    ident = row["id"]
    reg = row["registry"]
    name = row["journey"]
    cfg, live = source_config(row["organization_id"], row["project_id"])
    if not live:
        raise core.Rejected("The workspace binding is unavailable.")
    journey = check_target(
        db, row["organization_id"], row["project_id"], reg, name, cfg
    )
    selected = journeys.select(live, name)
    if row["status"] == "queued" and fingerprint(selected) != row["source_digest"]:
        raise core.Rejected(
            "Journey binding changed. Register it before requesting a replay."
        )
    if selected["profile"]["plan"]["id"] != journey["profile"]["plan"]["id"]:
        raise core.Rejected("Saved plan binding changed.")
    db.commit()
    client = capture_client(cfg)
    directory = core.private_dir(private_root() / str(ident))
    journal = directory / "start.jsonl"

    def verify_saved_steps():
        live_registry = {**live, "journeys": [selected]}
        observed = journeys.register(client, live_registry, name)
        if fingerprint(observed) != row["digest"]:
            raise core.Rejected(
                "Saved ContextQA cases or steps changed since registration."
            )

    if row["status"] == "queued":
        verify_saved_steps()
        preflight = journeys.inspect(client, journey)
        update(db, ident, "starting")
        accepted = client.trigger_run(
            journey["profile"]["plan"]["id"],
            journal,
            approve_execution=True,
            environment=journey["profile"]
            .get("execution", {})
            .get("query", {})
            .get("environment"),
            preflight=preflight,
        )
        update(db, ident, "running", run=accepted["run_id"])
        return
    if row["status"] == "starting":
        if not journal.exists():
            raise core.Rejected("Missing durable provider acceptance.")
        update(db, ident, "running", run=recorded_run(journal))
        return
    run = row["provider_run"]
    if not run:
        raise core.Rejected("An attributable accepted run is required.")
    if row["status"] == "running":
        poll = client.poll_run(run, max_attempts=1, deadline=18)
        if poll["summary"].get("status") != "STATUS_COMPLETED":
            if row["attempts"] >= 40:
                update(
                    db,
                    ident,
                    "reconcile",
                    "Polling window elapsed. Check the same provider run.",
                )
            else:
                update(db, ident, "running")
            return
        if poll["verdict"] != "passed":
            update(
                db,
                ident,
                "inconclusive",
                "The provider run did not pass every required check.",
            )
            return
        update(db, ident, "collecting")
    verified_path = directory / "capture-verified"
    # The trusted deployment receipt is supplied by the deployer after a run is known.
    deploy = None
    if cfg.get("deployment_receipt_directory"):
        proof = Path(cfg["deployment_receipt_directory"]) / (str(run) + ".json")
        if proof.is_file():
            deploy = core.load_json(proof)
    verified = journeys.deployment_check(deploy, journey, run, row["revision"])
    capture = verified_path if verified else directory / "capture"
    if not capture.exists():
        verify_saved_steps()
        attempt = directory / ("collect-" + uuid4().hex)
        journeys.capture(
            client,
            reg,
            name,
            run,
            row["revision"],
            attempt,
            deploy if verified else None,
        )
        attempt.rename(capture)
    record = journeys.checked(core.load_json(capture / "journey-capture.json"))
    if (
        record["run_id"] != run
        or record["head_sha"] != row["revision"]
        or record["journey"] != journey
    ):
        raise core.Rejected("Capture identity changed.")
    if record["receipt"]["verdict"] != "passed":
        update(
            db,
            ident,
            "inconclusive",
            "Selected case and step results did not establish a pass.",
        )
        return
    receipt = {
        "deployment_verified": verified,
        "verdict": "passed",
        "steps": record["receipt"]["step_results_read"],
        "cases": record["receipt"]["case_results_read"],
        "media": [],
    }
    gaps = cfg.get("coverage_gaps", {}).get(name, [])
    receipt["coverage_gaps"] = gaps
    if not verified or gaps:
        update(
            db,
            ident,
            "needs_evidence",
            "Provide the matching deployment receipt and resolve uncovered prerequisites.",
            receipt=receipt,
        )
        return
    if not (capture / "review-recipe.json").exists():
        journeys.fetch_capture_media(
            capture, cfg.get("capture_storage_hosts", []), max_files=20
        )
    manifest = core.manifest(capture)
    recipe = core.load_json(capture / "review-recipe.json")
    associations = {
        i: [s["step_result_id"] for s in recipe["steps"] if i in s.get("media_ids", [])]
        for i in (m["id"] for m in manifest["media"])
    }
    receipt["recipe_digest"] = fingerprint(recipe)
    receipt["instructions"] = [
        {k: s[k] for k in ("step_result_id", "title", "instruction")}
        for s in recipe["steps"]
    ]
    receipt["media"] = [
        {
            "id": m["id"],
            "kind": m["kind"],
            "sha256": m["sha256"],
            "step_results": associations[m["id"]],
        }
        for m in manifest["media"]
    ]
    if set(journey["required_media"]) - {m["kind"] for m in receipt["media"]}:
        update(
            db,
            ident,
            "needs_evidence",
            "The replay is missing a required media type.",
            receipt=receipt,
        )
        return
    update(db, ident, "awaiting_review", receipt=receipt)


def tick(pool):
    with pool.connection() as db, db.cursor(row_factory=dict_row) as cur:
        candidates = cur.execute("""SELECT id FROM docs_capture_jobs WHERE status IN('queued','starting','running','collecting')
            AND next_at<=now() ORDER BY next_at LIMIT 10""").fetchall()
        for candidate in candidates:
            ident = candidate["id"]
            locked = db.execute(
                "SELECT pg_try_advisory_lock(hashtextextended(%s,42))", (str(ident),)
            ).fetchone()[0]
            if not locked:
                continue
            try:
                current = cur.execute(
                    """SELECT * FROM docs_capture_jobs WHERE id=%s AND next_at<=now()
                    AND status IN('queued','starting','running','collecting')""",
                    (ident,),
                ).fetchone()
                if current:
                    try:
                        advance(db, current)
                    except Exception as exc:
                        db.rollback()
                        state = db.execute(
                            "SELECT status FROM docs_capture_jobs WHERE id=%s", (ident,)
                        ).fetchone()[0]
                        reason = {
                            "queued": "Verify the workspace binding, plan permission and saved definition before requesting a new replay.",
                            "starting": "Reconcile the private start journal with ContextQA before any new request.",
                            "running": "Restore provider read access and check the existing run.",
                            "collecting": "Inspect the private capture, deployment evidence and storage host binding.",
                        }[state]
                        update(
                            db,
                            ident,
                            "blocked" if state == "queued" else "reconcile",
                            reason,
                        )
                        logging.getLogger(__name__).warning(
                            "Capture paused (%s)", type(exc).__name__
                        )
                    return True
            finally:
                with suppress(Exception):
                    db.execute(
                        "SELECT pg_advisory_unlock(hashtextextended(%s,42))",
                        (str(ident),),
                    )
                    db.commit()
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    with ConnectionPool(os.environ["DATABASE_URL"]) as pool:
        while True:
            progress = tick(pool)
            if args.once:
                return
            if not progress:
                time.sleep(2)


if __name__ == "__main__":
    main()
