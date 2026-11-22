"""Run one transactional stage per claim. No stage makes an external write."""

import argparse
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .workflows import enqueue, scheduled_instant


def dispatch(pool, now=None):
    now = now or datetime.now(timezone.utc)
    with pool.connection() as db, db.cursor(row_factory=dict_row) as cur:
        flows = cur.execute(
            "SELECT * FROM docs_workflows WHERE active ORDER BY organization_id,project_id FOR UPDATE SKIP LOCKED"
        ).fetchall()
        for w in flows:
            key = (w["organization_id"], w["project_id"])
            conf = w["config"]
            if conf["trigger"] == "daily":
                day = now.astimezone(ZoneInfo(conf["timezone"])).date()
                at = scheduled_instant(day, conf["local_time"], conf["timezone"])
                if at > now:
                    day -= timedelta(days=1)
                    at = scheduled_instant(day, conf["local_time"], conf["timezone"])
                if at < w["activated_at"] or (
                    w["last_schedule"] and day <= w["last_schedule"]
                ):
                    continue
                enqueue(
                    db, w, "daily", day.isoformat(), {"scheduled_for": at.isoformat()}
                )
                db.execute(
                    "UPDATE docs_workflows SET last_schedule=%s,live_cursor=%s WHERE organization_id=%s AND project_id=%s",
                    (day, day.isoformat(), *key),
                )
            else:
                rows = cur.execute(
                    """SELECT DISTINCT ON (d.repository,d.revision) d.repository,d.revision,d.item_id FROM docs_source_deliveries d
                    JOIN docs_setup s USING(organization_id,project_id)
                    WHERE d.organization_id=%s AND d.project_id=%s AND s.connected AND s.product_repo=d.repository
                    AND NOT EXISTS(SELECT 1 FROM docs_runs r WHERE r.organization_id=d.organization_id AND r.project_id=d.project_id
                    AND r.mode='github' AND r.trigger_key=d.repository||'@'||d.revision)
                    ORDER BY d.repository,d.revision,d.received_at LIMIT 100""",
                    key,
                ).fetchall()
                for source in rows:
                    handle = source["repository"] + "@" + source["revision"]
                    enqueue(db, w, "github", handle, source)
                    db.execute(
                        "UPDATE docs_workflows SET live_cursor=%s WHERE organization_id=%s AND project_id=%s",
                        (handle, *key),
                    )


def claim(pool):
    token = uuid4()
    with pool.connection() as db:
        db.execute("""UPDATE docs_runs SET status='needs_input', reason='Repeated worker interruptions. Check worker health, then resume.',
            lease=NULL,expires_at=NULL,updated_at=now() WHERE status='running' AND expires_at<now() AND stage_attempts>=3""")
        row = db.execute(
            """WITH next AS (SELECT r.id FROM docs_runs r JOIN docs_workflows w USING(organization_id,project_id)
            WHERE (w.active OR r.mode='test' OR r.stage>0 OR r.status='running')
            AND (r.status='queued' OR (r.status='running' AND r.expires_at<now()))
            ORDER BY r.updated_at FOR UPDATE OF r SKIP LOCKED LIMIT 1)
            UPDATE docs_runs r SET status='running',lease=%s,expires_at=now()+interval '30 seconds',
            attempts=r.attempts+1,stage_attempts=r.stage_attempts+1,updated_at=now() FROM next WHERE r.id=next.id RETURNING r.id""",
            (token,),
        ).fetchone()
        return (row[0], token) if row else None


def checkpoint(pool, ident, token):
    with pool.connection() as db, db.cursor(row_factory=dict_row) as cur:
        run = cur.execute(
            """SELECT r.*,v.config FROM docs_runs r JOIN docs_workflow_versions v ON
            (r.organization_id,r.project_id,r.workflow_version)=(v.organization_id,v.project_id,v.version)
            WHERE r.id=%s AND r.lease=%s AND r.expires_at>now() FOR UPDATE OF r""",
            (ident, token),
        ).fetchone()
        if not run:
            return False
        key = (run["organization_id"], run["project_id"])
        index = run["stage"]
        project = cur.execute(
            "SELECT state FROM docs_projects WHERE organization_id=%s AND id=%s", key
        ).fetchone()["state"]
        reason = None
        if index == 0:
            item_id = run["input"].get("item_id")
            if run["mode"] == "github" and item_id not in project["items"]:
                reason = "Restore the linked source review item before resuming."
            receipt = {
                "name": "Source checked",
                "mode": run["mode"],
                "source": run["trigger_key"],
                "item_id": item_id,
            }
        elif index == 1:
            paths = sorted(project["articles"])
            if not paths:
                reason = "Import an article in Knowledge base, then resume this run."
            if len(paths) > run["config"]["page_limit"]:
                reason = "Inventory exceeds this version’s page limit. Save a larger limit and start a new run."
            receipt = {
                "name": "Inventory checked",
                "pages": len(paths),
                "paths": paths[: run["config"]["page_limit"]],
            }
        else:
            inventory = cur.execute(
                "SELECT receipt FROM docs_run_stages WHERE run_id=%s AND stage=1",
                (ident,),
            ).fetchone()["receipt"]
            receipt = {
                "name": "Research brief prepared",
                "instructions": run["config"]["instructions"],
                "source_item": run["input"].get("item_id"),
                "candidate_paths": inventory["paths"],
                "next_action": "Review source impact and select journeys for capture.",
            }
        if reason:
            db.execute(
                "UPDATE docs_runs SET status='needs_input',reason=%s,lease=NULL,expires_at=NULL,updated_at=now() WHERE id=%s",
                (reason, ident),
            )
            return True
        db.execute(
            "INSERT INTO docs_run_stages(run_id,stage,receipt) VALUES(%s,%s,%s)",
            (ident, index, Jsonb(receipt)),
        )
        db.execute(
            "UPDATE docs_runs SET stage=stage+1,stage_attempts=0,status=%s,reason=NULL,lease=NULL,expires_at=NULL,updated_at=now() WHERE id=%s",
            ("succeeded" if index == 2 else "queued", ident),
        )
        return True


def tick(pool):
    dispatch(pool)
    task = claim(pool)
    return bool(task and checkpoint(pool, *task))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="Dispatch and checkpoint at most one stage."
    )
    args = parser.parse_args()
    with ConnectionPool(os.environ["DATABASE_URL"]) as pool:
        while True:
            try:
                progress = tick(pool)
            except Exception as exc:
                logging.getLogger(__name__).error(
                    "Workflow worker iteration failed (%s)", type(exc).__name__
                )
                if args.once:
                    raise
                progress = False
            if args.once:
                return
            if not progress:
                time.sleep(2)


if __name__ == "__main__":
    main()
