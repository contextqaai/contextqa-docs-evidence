"""Versioned workspace workflows and explicit backlog decisions."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .inventory import access
from .onboarding import PREFIX


class Version(BaseModel):
    version: int = Field(ge=0)


class Spec(Version):
    instructions: str = Field(min_length=1, max_length=2400)
    trigger: Literal["github", "daily"]
    timezone: str = Field(max_length=128)
    local_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    page_limit: int = Field(ge=1, le=500)


class Activation(Version):
    backlog: Literal["process", "skip"]


class TestRun(Version):
    request_id: UUID


def scheduled_instant(day: date, local_time: str, zone: str):
    tz = ZoneInfo(zone)
    wall = datetime.combine(day, time.fromisoformat(local_time))
    # A fold runs at its first instant. A gap runs at the first valid local minute.
    for minute in range(1441):
        candidate = wall + timedelta(minutes=minute)
        utc = candidate.replace(tzinfo=tz, fold=0).astimezone(timezone.utc)
        if utc.astimezone(tz).replace(tzinfo=None) == candidate:
            return utc
    raise ValueError("Unavailable local calendar date")


def record(db, org, project, lock=False):
    with db.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT * FROM docs_workflows WHERE organization_id=%s AND project_id=%s"
            + (" FOR UPDATE" if lock else ""),
            (org, project),
        ).fetchone()


def expected(row, version):
    if (row["version"] if row else 0) != version:
        raise HTTPException(409, "Workflow changed. Reload before saving.")


def enqueue(db, w, mode, key, payload):
    row = db.execute(
        """INSERT INTO docs_runs(id,organization_id,project_id,workflow_version,mode,trigger_key,input)
        VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (organization_id,project_id,mode,trigger_key) DO NOTHING RETURNING id""",
        (
            uuid4(),
            w["organization_id"],
            w["project_id"],
            w["version"],
            mode,
            key,
            Jsonb(payload),
        ),
    ).fetchone()
    return row[0] if row else None


def status(db, org, project):
    with db.cursor(row_factory=dict_row) as cur:
        history = cur.execute(
            """SELECT id,workflow_version,mode,status,stage,attempts,created_at,reason FROM docs_runs
            WHERE organization_id=%s AND project_id=%s ORDER BY created_at DESC LIMIT 50""",
            (org, project),
        ).fetchall()
    return {"workflow": record(db, org, project), "runs": history}


def router(pool, auth):
    routes = APIRouter()
    actor_dep = Depends(auth)
    base = PREFIX + "/workflow"

    @routes.get(base)
    def get(org: str, project: str, actor=actor_dep):
        with pool.connection() as db:
            access(db, org, project, actor)
            return status(db, org, project)

    @routes.post(base + "/save")
    def save(org: str, project: str, body: Spec, actor=actor_dep):
        try:
            ZoneInfo(body.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(
                422, "Choose an IANA time zone such as America/Chicago."
            ) from None
        conf = body.model_dump(exclude={"version"})
        conf["instructions"] = conf["instructions"].strip()
        if not conf["instructions"]:
            raise HTTPException(422, "Describe the documentation task.")
        with pool.connection() as db:
            access(db, org, project, actor)
            db.execute(
                "SELECT id FROM docs_projects WHERE organization_id=%s AND id=%s FOR UPDATE",
                (org, project),
            )
            w = record(db, org, project, True)
            expected(w, body.version)
            if (
                w
                and w["active"]
                and any(
                    w["config"][k] != conf[k]
                    for k in ("trigger", "timezone", "local_time")
                )
            ):
                raise HTTPException(
                    409, "Pause the workflow before changing its trigger or schedule."
                )
            version = body.version + 1
            db.execute(
                """INSERT INTO docs_workflows(organization_id,project_id,version,config) VALUES(%s,%s,%s,%s)
                ON CONFLICT(organization_id,project_id) DO UPDATE SET version=excluded.version,config=excluded.config""",
                (org, project, version, Jsonb(conf)),
            )
            db.execute(
                "INSERT INTO docs_workflow_versions(organization_id,project_id,version,config,actor) VALUES(%s,%s,%s,%s,%s)",
                (org, project, version, Jsonb(conf), actor),
            )
            return status(db, org, project)

    @routes.post(base + "/activate")
    def activate(org: str, project: str, body: Activation, actor=actor_dep):
        with pool.connection() as db:
            access(db, org, project, actor)
            w = record(db, org, project, True)
            expected(w, body.version)
            if not w:
                raise HTTPException(409, "Save a workflow first.")
            if not w["active"]:
                if w["config"]["trigger"] == "github":
                    repo = db.execute(
                        "SELECT product_repo FROM docs_setup WHERE organization_id=%s AND project_id=%s AND connected",
                        (org, project),
                    ).fetchone()
                    if not repo:
                        raise HTTPException(
                            409,
                            "Connect the product repository in Workspace settings before activating this source.",
                        )
                    if body.backlog == "skip":
                        db.execute(
                            """INSERT INTO docs_runs(id,organization_id,project_id,workflow_version,mode,trigger_key,input,status,reason)
                          SELECT gen_random_uuid(),%s,%s,%s,'github',repository||'@'||revision,'{}','skipped','Backlog skipped at activation'
                          FROM (SELECT DISTINCT repository,revision FROM docs_source_deliveries WHERE organization_id=%s AND project_id=%s AND repository=%s) s
                          ON CONFLICT(organization_id,project_id,mode,trigger_key) DO NOTHING""",
                            (org, project, w["version"], org, project, repo[0]),
                        )
                db.execute(
                    "UPDATE docs_workflows SET active=true,activated_at=CASE WHEN %s THEN now()-interval '2 days' ELSE now() END WHERE organization_id=%s AND project_id=%s",
                    (
                        body.backlog == "process" and w["config"]["trigger"] == "daily",
                        org,
                        project,
                    ),
                )
            return status(db, org, project)

    @routes.post(base + "/pause")
    def pause(org: str, project: str, body: Version, actor=actor_dep):
        with pool.connection() as db:
            access(db, org, project, actor)
            expected(record(db, org, project, True), body.version)
            db.execute(
                "UPDATE docs_workflows SET active=false WHERE organization_id=%s AND project_id=%s",
                (org, project),
            )
            return status(db, org, project)

    @routes.post(base + "/test")
    def test(org: str, project: str, body: TestRun, actor=actor_dep):
        with pool.connection() as db:
            access(db, org, project, actor)
            w = record(db, org, project, True)
            expected(w, body.version)
            if not w:
                raise HTTPException(409, "Save a workflow before testing it.")
            k = str(body.request_id)
            prior = db.execute(
                "SELECT id FROM docs_runs WHERE organization_id=%s AND project_id=%s AND mode='test' AND trigger_key=%s",
                (org, project, k),
            ).fetchone()
            if prior:
                return {"id": prior[0]}
            if db.execute(
                "SELECT 1 FROM docs_runs WHERE organization_id=%s AND project_id=%s AND mode='test' AND status IN('queued','running')",
                (org, project),
            ).fetchone():
                raise HTTPException(
                    409, "A test is already running. Open its timeline."
                )
            return {"id": enqueue(db, w, "test", k, {"requested_by": actor})}

    @routes.get(base + "/runs/{ident}")
    def detail(org: str, project: str, ident: UUID, actor=actor_dep):
        with pool.connection() as db, db.cursor(row_factory=dict_row) as cur:
            access(db, org, project, actor)
            run = cur.execute(
                """SELECT r.id,r.mode,r.status,r.reason,r.stage,r.workflow_version,r.attempts,v.config FROM docs_runs r JOIN docs_workflow_versions v
                ON (r.organization_id,r.project_id,r.workflow_version)=(v.organization_id,v.project_id,v.version)
                WHERE r.id=%s AND r.organization_id=%s AND r.project_id=%s""",
                (ident, org, project),
            ).fetchone()
            if not run:
                raise HTTPException(404, "Run unavailable.")
            run["receipts"] = cur.execute(
                "SELECT stage,receipt,completed_at FROM docs_run_stages WHERE run_id=%s ORDER BY stage",
                (ident,),
            ).fetchall()
            return run

    @routes.post(base + "/runs/{ident}/resume")
    def resume(org: str, project: str, ident: UUID, actor=actor_dep):
        with pool.connection() as db:
            access(db, org, project, actor)
            record(db, org, project, True)
            row = db.execute(
                "SELECT mode,status FROM docs_runs WHERE id=%s AND organization_id=%s AND project_id=%s FOR UPDATE",
                (ident, org, project),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Run unavailable.")
            if row[1] != "needs_input":
                raise HTTPException(409, "Only a run waiting for input can resume.")
            if (
                row[0] == "test"
                and db.execute(
                    "SELECT 1 FROM docs_runs WHERE organization_id=%s AND project_id=%s AND mode='test' AND status IN('queued','running')",
                    (org, project),
                ).fetchone()
            ):
                raise HTTPException(409, "Wait for the current test to finish.")
            db.execute(
                "UPDATE docs_runs SET status='queued',stage_attempts=0,reason=NULL,updated_at=now() WHERE id=%s",
                (ident,),
            )
            return status(db, org, project)

    return routes
