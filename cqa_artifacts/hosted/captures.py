"""Workspace-scoped saved journey registration and replay requests."""

from pathlib import Path
from uuid import UUID, uuid4
import os

from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .. import core, journeys
from ..contextqa import ContextQAClient, recorded_run
from ..loop import fingerprint
from .inventory import access
from .onboarding import PREFIX, admin, binding, setup


class Replay(BaseModel):
    request_id: UUID
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    confirm: bool


class EvidenceReview(BaseModel):
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirm: bool


def private_root():
    path = os.environ.get("DOCS_CAPTURE_ROOT")
    if not path:
        raise HTTPException(
            409, "Mount a private capture directory on both the API and worker."
        )
    return Path(path)


def source_config(org, project):
    cfg = binding(org, project)
    filename = cfg.get("capture_registry_file")
    if not filename:
        return cfg, None
    try:
        return cfg, journeys.registry(core.load_json(Path(filename)))
    except (OSError, ValueError):
        raise HTTPException(
            409, "The configured journey registry is unreadable or invalid."
        ) from None


def check_target(db, org, project, registry, ident, cfg):
    journey = journeys.select(registry, ident)
    current = setup(db, org, project)
    if (
        cfg.get("workspace_version_id") != journey["workspace_version_id"]
        or not current["app_url"]
        or current["app_url"] != cfg.get("app_url")
        or current["app_url"] != journey["application_url"]
        or registry["repository"] != current["product_repo"]
    ):
        raise HTTPException(
            409,
            "Journey workspace, product repository or application URL differs from its binding.",
        )
    if journey["profile"]["plan"]["id"] not in cfg.get("capture_plan_ids", []):
        raise HTTPException(
            409, "Authorize this saved plan in the workspace connection first."
        )
    return journey


def capture_client(cfg):
    if not cfg.get("capture_api_token"):
        raise HTTPException(409, "Configure the workspace ContextQA API credential.")
    return ContextQAClient(cfg["capture_api_token"])


def router(pool, auth):
    routes = APIRouter()
    actor_dep = Depends(auth)
    base = PREFIX + "/captures"

    @routes.get(base)
    def overview(org: str, project: str, actor=actor_dep):
        with pool.connection() as db, db.cursor(row_factory=dict_row) as cur:
            access(db, org, project, actor)
            cfg, reg = source_config(org, project)
            saved = {
                name: (digest, source)
                for name, digest, source in (
                    db.execute(
                        "SELECT journey,digest,source_digest FROM docs_capture_profiles WHERE organization_id=%s AND project_id=%s",
                        (org, project),
                    ).fetchall()
                )
            }
            rows = cur.execute(
                """SELECT id,journey,revision,status,reason,provider_run,receipt,created_at FROM docs_capture_jobs
                WHERE organization_id=%s AND project_id=%s ORDER BY created_at DESC LIMIT 50""",
                (org, project),
            ).fetchall()
            discovery = db.execute(
                "SELECT status FROM docs_discoveries WHERE organization_id=%s AND project_id=%s ORDER BY created_at DESC LIMIT 1",
                (org, project),
            ).fetchone()
            return {
                "discovery": discovery[0] if discovery else None,
                "provider_configured": bool(cfg.get("capture_api_token")),
                "profiles": [
                    {
                        "id": j["id"],
                        "name": j["name"],
                        "cases": j["case_ids"],
                        "plan": j["profile"]["plan"]["id"],
                        "environment": j["environment"],
                        "digest": saved[j["id"]][0]
                        if saved.get(j["id"], (None, None))[1] == fingerprint(j)
                        else None,
                        "drift": j["id"] in saved
                        and saved[j["id"]][1] != fingerprint(j),
                    }
                    for j in (reg or {}).get("journeys", [])
                ],
                "jobs": [
                    {
                        **r,
                        "receipt_digest": fingerprint(r["receipt"])
                        if r["receipt"]
                        else None,
                    }
                    for r in rows
                ],
                "meter": cfg.get("capture_meter_note"),
                "workspace": cfg.get("workspace_version_id"),
            }

    @routes.post(base + "/{ident}/register")
    def register(org: str, project: str, ident: str, actor=actor_dep):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg, reg = source_config(org, project)
            if not reg:
                raise HTTPException(409, "Configure the workspace journey registry.")
            check_target(db, org, project, reg, ident, cfg)
        # Adopt only this plan. An edit to a different profile cannot alter this snapshot.
        scoped = {**reg, "journeys": [journeys.select(reg, ident)]}
        locked = journeys.register(capture_client(cfg), scoped, ident)
        digest = fingerprint(locked)
        with pool.connection() as db:
            admin(db, org, actor)
            updated, live = source_config(org, project)
            if not live or journeys.select(live, ident) != scoped["journeys"][0]:
                raise HTTPException(
                    409, "Journey configuration changed during registration."
                )
            check_target(db, org, project, locked, ident, updated)
            db.execute(
                """INSERT INTO docs_capture_profiles(organization_id,project_id,journey,digest,registry,source_digest)
                VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(organization_id,project_id,journey) DO UPDATE
                SET digest=excluded.digest,registry=excluded.registry,source_digest=excluded.source_digest,registered_at=now()""",
                (
                    org,
                    project,
                    ident,
                    digest,
                    Jsonb(locked),
                    fingerprint(scoped["journeys"][0]),
                ),
            )
        return {"digest": digest}

    @routes.post(base + "/{ident}/replay")
    def replay(org: str, project: str, ident: str, body: Replay, actor=actor_dep):
        if not body.confirm:
            raise HTTPException(422, "Confirm the metered saved-plan replay.")
        private_root()
        with pool.connection() as db:
            admin(db, org, actor)
            prior = db.execute(
                "SELECT id,journey,revision,digest FROM docs_capture_jobs WHERE organization_id=%s AND project_id=%s AND request_id=%s",
                (org, project, body.request_id),
            ).fetchone()
            if prior:
                if prior[1:] != (ident, body.revision, body.digest):
                    raise HTTPException(
                        409, "Request identifier belongs to a different replay."
                    )
                return {"id": prior[0]}
            saved = db.execute(
                "SELECT registry,digest,source_digest FROM docs_capture_profiles WHERE organization_id=%s AND project_id=%s AND journey=%s",
                (org, project, ident),
            ).fetchone()
            if not saved or body.digest != saved[1]:
                raise HTTPException(
                    409, "Register the current journey definition before replay."
                )
            cfg, reg = source_config(org, project)
            if not reg:
                raise HTTPException(409, "The journey binding was removed.")
            if fingerprint(journeys.select(reg, ident)) != saved[2]:
                raise HTTPException(
                    409, "The saved journey configuration changed. Register it again."
                )
            check_target(db, org, project, saved[0], ident, cfg)
            if not cfg.get("capture_meter_note") or not cfg.get("capture_api_token"):
                raise HTTPException(
                    409,
                    "Configure the workspace credential and metering terms before replay.",
                )
            current = db.execute(
                """SELECT id FROM docs_capture_jobs WHERE organization_id=%s AND project_id=%s AND journey=%s AND revision=%s AND digest=%s
                AND status IN('queued','starting','running','collecting','reconcile','needs_evidence','awaiting_review')""",
                (org, project, ident, body.revision, body.digest),
            ).fetchone()
            if current:
                return {"id": current[0]}
            job = uuid4()
            db.execute(
                """INSERT INTO docs_capture_jobs(id,organization_id,project_id,request_id,journey,digest,registry,revision,source_digest,status)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued')""",
                (
                    job,
                    org,
                    project,
                    body.request_id,
                    ident,
                    body.digest,
                    Jsonb(saved[0]),
                    body.revision,
                    saved[2],
                ),
            )
            return {"id": job}

    def get_job(db, org, project, job):
        with db.cursor(row_factory=dict_row) as cur:
            row = cur.execute(
                "SELECT * FROM docs_capture_jobs WHERE organization_id=%s AND project_id=%s AND id=%s FOR UPDATE",
                (org, project, job),
            ).fetchone()
        if not row:
            raise HTTPException(404, "Capture unavailable.")
        return row

    @routes.post(base + "/jobs/{job}/check")
    def check(org: str, project: str, job: UUID, actor=actor_dep):
        with pool.connection() as db:
            admin(db, org, actor)
            row = get_job(db, org, project, job)
            if row["status"] not in ("reconcile", "needs_evidence"):
                raise HTTPException(409, "Only stopped captures can be checked again.")
            run = row["provider_run"]
            if not run:
                journal = private_root() / str(job) / "start.jsonl"
                if not journal.is_file():
                    raise HTTPException(
                        409,
                        "ContextQA acceptance is unknown. Check the original run with the provider.",
                    )
                run = recorded_run(journal)
            db.execute(
                "UPDATE docs_capture_jobs SET status='running', provider_run=%s,reason=NULL,next_at=now(),attempts=0 WHERE id=%s",
                (run, job),
            )
            return {"id": job, "provider_run": run}

    @routes.get(base + "/jobs/{job}/media/{media}")
    def media(org: str, project: str, job: UUID, media: str, actor=actor_dep):
        with pool.connection() as db:
            access(db, org, project, actor)
            row = get_job(db, org, project, job)
            item = next(
                (
                    m
                    for m in (row["receipt"] or {}).get("media", [])
                    if m["id"] == media
                ),
                None,
            )
            if not item or row["status"] not in ("awaiting_review", "reviewed"):
                raise HTTPException(404, "Capture media unavailable.")
        root = private_root() / str(job) / "capture-verified"
        source = next(
            (m for m in core.manifest(root)["media"] if m["id"] == media), None
        )
        if not source:
            raise HTTPException(409, "Captured file is missing.")
        payload = core.regular_file(core.asset_file(root, source["path"]))
        if core.digest(payload) != item["sha256"]:
            raise HTTPException(409, "Captured file changed.")
        suffix = core.media_extension(payload, item["kind"])
        mime = {
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
        }[suffix]
        return Response(
            payload, media_type=mime, headers={"X-Content-Type-Options": "nosniff"}
        )

    @routes.post(base + "/jobs/{job}/review")
    def review(
        org: str, project: str, job: UUID, body: EvidenceReview, actor=actor_dep
    ):
        with pool.connection() as db:
            access(db, org, project, actor)
            row = get_job(db, org, project, job)
            if (
                not body.confirm
                or row["status"] not in ("awaiting_review", "reviewed")
                or body.digest != fingerprint(row["receipt"])
            ):
                raise HTTPException(
                    409,
                    "Review the current evidence and confirm content and media rights.",
                )
            if row["status"] == "reviewed":
                return {"id": job, "status": "reviewed"}
            directory = private_root() / str(job)
            root = directory / "capture-verified"
            recipe = core.load_json(root / "review-recipe.json")
            if fingerprint(recipe) != row["receipt"]["recipe_digest"]:
                raise HTTPException(409, "Capture steps or media selection changed.")
            dest = directory / "reviewed"
            if not dest.exists():
                staged = directory / ("review-" + uuid4().hex)
                journeys.review_capture(root, recipe, staged, actor, True)
                staged.rename(dest)
            stored = journeys.checked(core.load_json(dest / "journey-review.json"))
            if (
                stored["head_sha"] != row["revision"]
                or stored["run_id"] != row["provider_run"]
            ):
                raise HTTPException(409, "Review export differs from the selected run.")
            db.execute(
                "UPDATE docs_capture_jobs SET status='reviewed' WHERE id=%s", (job,)
            )
            return {"id": job, "status": "reviewed"}

    return routes
