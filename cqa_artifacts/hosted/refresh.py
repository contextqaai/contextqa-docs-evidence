"""Track affected approved guides when a signed product change is accepted."""

import fnmatch
from psycopg.types.json import Jsonb


def record(db, org, project, event, item):
    if not event.get("revision"):
        return
    rows = db.execute(
        """SELECT h.path,h.digest,v.source,v.media FROM docs_guide_heads h JOIN docs_guide_versions v
        USING(organization_id,project_id,path,digest) WHERE h.organization_id=%s AND h.project_id=%s""",
        (org, project),
    ).fetchall()
    if not rows:
        return
    manifest = db.execute(
        "SELECT state->'manifest' FROM docs_projects WHERE organization_id=%s AND id=%s",
        (org, project),
    ).fetchone()[0]
    for path, base, source, media in rows:
        sections = [s for s in manifest["sections"] if s["path"] == path]
        patterns = set(source.get("changed_paths", []))
        for section in sections:
            patterns.update(section.get("code_paths", []))
        modules = set(source.get("module_ids", []))
        for section in sections:
            modules.update(section.get("module_ids", []))
        if not (
            any(
                fnmatch.fnmatchcase(p, g)
                for p in event.get("changed_paths", [])
                for g in patterns
            )
            or modules.intersection(event.get("module_ids", []))
        ):
            continue
        db.execute(
            """INSERT INTO docs_refresh_requests(organization_id,project_id,path,base,revision,item_id,journeys)
             VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (
                org,
                project,
                path,
                base,
                event["revision"],
                item,
                Jsonb(sorted({m["journey"] for m in media})),
            ),
        )


def refresh_one(db, row):
    from datetime import datetime, timezone
    from pathlib import Path
    from uuid import uuid5, NAMESPACE_URL
    from fastapi import HTTPException
    from .. import core, journeys
    from ..loop import fingerprint
    from .captures import source_config, check_target
    from .editorial import Brief, capture_for, compiled
    from .github_intake import BoundConnection
    from .onboarding import setup
    from .store import PostgresStore
    import re

    org, project, path, base, rev, names, source_item = row
    key = (org, project)
    cfg, reg = source_config(org, project)
    # Operators opt in per registered plan; source events cannot grant paid execution.
    if (
        not reg
        or not cfg.get("auto_refresh_plans")
        or not cfg.get("deployment_revision_file")
    ):
        return "waiting", "Configure metered refresh and a deployment receipt.", None
    current = setup(db, org, project)
    if not current["connected"]:
        return "waiting", "The product connection is paused.", None
    latest = db.execute(
        "SELECT digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s AND path=%s",
        (*key, path),
    ).fetchone()
    if not latest or latest[0] != base:
        return "superseded", "The approved guide advanced.", None
    try:
        deployment = core.load_json(Path(cfg["deployment_revision_file"]))
    except (OSError, ValueError):
        return "waiting", "Waiting for the deployed revision receipt.", None
    if (
        not isinstance(deployment, dict)
        or deployment.get("commit_sha") != rev
        or deployment.get("application_url") != current["app_url"]
        or deployment.get("repository") != current["product_repo"]
    ):
        return "waiting", "Waiting for the matching deployment.", None
    store = PostgresStore(BoundConnection(db), org)
    actor = current["connected_by"]
    state = store.snapshot(project, actor)
    source = state["items"][source_item]
    event = state["events"][source["event_id"]]["event"]
    previous = db.execute(
        "SELECT body,item_id FROM docs_guide_versions WHERE organization_id=%s AND project_id=%s AND path=%s AND digest=%s",
        (*key, path, base),
    ).fetchone()
    baseline = state["articles"].get(path, {}).get("body", "")
    if baseline != previous[0]:
        return "waiting", "Import the delivered baseline before refreshing.", None
    original = state["items"].get(previous[1], {})
    if len(names) != 1 or not original.get("writing", {}).get("brief"):
        return (
            "investigate",
            "An editor must map this guide to a single scoped writing brief.",
            None,
        )
    name = names[0]
    saved = db.execute(
        "SELECT registry,digest,source_digest FROM docs_capture_profiles WHERE organization_id=%s AND project_id=%s AND journey=%s",
        (*key, name),
    ).fetchone()
    if not saved or fingerprint(journeys.select(reg, name)) != saved[2]:
        return "waiting", "Register the current journey definition.", None
    j = check_target(db, org, project, saved[0], name, cfg)
    if (
        j["profile"]["plan"]["id"] not in cfg["auto_refresh_plans"]
        or not cfg.get("capture_meter_note")
        or not cfg.get("capture_api_token")
    ):
        return "waiting", "Configure this saved plan for metered refresh.", None
    job = db.execute(
        """SELECT id,status FROM docs_capture_jobs WHERE organization_id=%s AND project_id=%s AND journey=%s AND revision=%s AND digest=%s
      ORDER BY created_at DESC LIMIT 1""",
        (*key, name, rev, saved[1]),
    ).fetchone()
    if not job:
        ident = uuid5(NAMESPACE_URL, fingerprint([org, project, name, rev, saved[1]]))
        db.execute(
            """INSERT INTO docs_capture_jobs(id,organization_id,project_id,request_id,journey,digest,registry,revision,source_digest,status)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued') ON CONFLICT DO NOTHING""",
            (ident, *key, ident, name, saved[1], Jsonb(saved[0]), rev, saved[2]),
        )
        return "capturing", "A saved plan is queued for this revision.", None
    ident, status = job
    if status != "reviewed":
        if status in ("inconclusive", "failed", "reconcile", "blocked"):
            return (
                "investigate",
                "Capture "
                + str(ident)
                + " requires investigation. The current guide is preserved.",
                None,
            )
        return "capturing", "Capture " + str(ident) + " is " + status + ".", None
    cap = capture_for(db, org, project, ident, event)
    brief = Brief(**{**original["writing"]["brief"], "capture": ident})
    guide, report = compiled(
        brief,
        original,
        {"observed_at": datetime.now(timezone.utc).date().isoformat()},
        cap,
    )
    markers = re.findall(r"<!-- contextqa:editorial:([a-zA-Z0-9-]+) -->", baseline)
    if len(markers) != 1:
        return "investigate", "Select the exact managed section to refresh.", None
    from .editorial import propose

    scratch = {"id": markers[0], "event_id": event["id"], "changes": []}
    propose(scratch, {path: {"body": baseline}}, path, guide, brief.goal)
    if not scratch["changes"]:
        return "no_change", "Reader content and media are unchanged.", None
    after = scratch["changes"][0]["after"]

    def visible(value):
        return re.sub(r"evidence/[0-9a-f]{64}/assets/", "evidence/assets/", value)

    if visible(after) == visible(baseline):
        return "no_change", "Reader content and media are unchanged.", None
    destination = {k: current[k] for k in ("docs_repo", "branch", "docs_root")}
    receipt = cap[2]
    ev = dict(
        id="guide:refresh:"
        + fingerprint([*key, path, base, rev, receipt["export_digest"]]),
        source="github",
        revision=rev,
        title=original["title"],
        text=event["text"],
        source_url=event.get("source_url"),
        documentation_destination=destination,
        changed_paths=event.get("changed_paths", []),
        journey_requirements=[
            dict(
                journey_id=name,
                source_sha256=receipt["source_sha256"],
                export_digest=receipt["export_digest"],
            )
        ],
        edits=[
            dict(
                path=path,
                before=baseline,
                after=after,
                reason="Updated from reviewed ContextQA replay",
            )
        ],
    )
    outcome = store.ingest(project, actor, ev)
    proposal = outcome["item_id"]
    if not outcome["duplicate"]:
        store.attach_evidence(project, actor, proposal, 1, cap[0])
        with store.transaction(project) as s:
            item = s["items"][proposal]
            item["writing"] = {
                **original["writing"],
                "brief": brief.model_dump(mode="json"),
                "destination": destination,
                "status": "drafted",
                "report": report,
                "request": None,
                "item_version": item["version"],
            }
    return "awaiting_review", "Review the proposed section and evidence.", proposal


def tick(pool):
    from ..core import Rejected
    from fastapi import HTTPException

    with pool.connection() as db:
        row = db.execute("""SELECT organization_id,project_id,path,base,revision,journeys,item_id FROM docs_refresh_requests
           WHERE status IN('waiting','capturing') AND next_at<=now() ORDER BY next_at FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if not row:
            return False
        try:
            with db.transaction():
                status, reason, proposal = refresh_one(db, row)
        except (Rejected, HTTPException, KeyError, ValueError, OSError):
            status, reason, proposal = (
                "investigate",
                "Review the workspace binding, guide baseline and capture receipts.",
                None,
            )
        db.execute(
            """UPDATE docs_refresh_requests SET status=%s,reason=%s,proposal=%s,next_at=now()+interval '2 minutes'
          WHERE organization_id=%s AND project_id=%s AND path=%s AND revision=%s""",
            (status, reason, proposal, row[0], row[1], row[2], row[4]),
        )
        return True
