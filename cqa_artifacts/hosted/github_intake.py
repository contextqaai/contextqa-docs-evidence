"""GitHub installation-scoped discovery and atomic source-event ingestion."""

import hashlib
import hmac
import json
import re
import time
import jwt
from contextlib import nullcontext
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool

from .onboarding import PREFIX, SLUG, admin, binding, expect_revision, setup
from .store import PostgresStore
from ..loop_sources import github_event


class Scope(BaseModel):
    revision: int = Field(ge=0)
    product_repo: str = Field(pattern="^" + SLUG + "$")
    docs_repo: str = Field(pattern="^" + SLUG + "$")
    branch: str = Field(min_length=1, max_length=200)
    docs_root: str = Field(max_length=300)


class Version(BaseModel):
    revision: int = Field(ge=0)


def github_access(config, *, permissions=None, repository=None):
    """Mint a short-lived installation token with the requested scope. Default to read-only."""
    if config.get("installation_token") or not config.get("app_private_key"):
        return config
    ident = str(config.get("installation_id", ""))
    if not ident.isdecimal() or not config.get("app_id"):
        raise HTTPException(503, "GitHub App installation binding is incomplete.")
    now = int(time.time())
    try:
        signed = jwt.encode({"iat":now-60,"exp":now+540,"iss":str(config["app_id"])},
                            config["app_private_key"],algorithm="RS256")
        response = httpx.post(f"https://api.github.com/app/installations/{ident}/access_tokens",
                              headers={"Authorization":"Bearer "+signed, "Accept":"application/vnd.github+json"},
                              json={"permissions": permissions or {"contents": "read"},
                                    **({"repositories": [repository]} if repository else {})}, timeout=10)
        response.raise_for_status()
        return {**config,"installation_token":response.json()["token"]}
    except (KeyError, ValueError, jwt.PyJWTError, httpx.HTTPError):
        raise HTTPException(502,"GitHub installation authentication failed.") from None


def github_get(config, path, params=None):
    token = config.get("installation_token")
    if not token:
        raise HTTPException(503, "Configure a GitHub installation credential for this workspace.")
    try:
        response = httpx.get(
            "https://api.github.com" + path,
            params=params,
            timeout=10,
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        return response.json()
    except (ValueError, httpx.HTTPError):
        raise HTTPException(
            502, "GitHub could not verify access. Check or renew the installation credential."
        ) from None


def repositories(config):
    result = {}
    for page in range(1, 101):
        rows = github_get(config, "/installation/repositories", {"page": page, "per_page": 100})[
            "repositories"
        ]
        result.update({r["full_name"]: r["default_branch"] for r in rows})
        if len(rows) < 100:
            return result
    raise HTTPException(422, "Narrow the installation scope before selecting repositories.")


def verify_signature(raw, headers, config):
    secret = config.get("webhook_secret", "")
    if len(secret) < 24:
        raise HTTPException(503, "Webhook signing secret unavailable.")
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    sig = headers.get("x-hub-signature-256", "")
    if not sig.isascii() or not hmac.compare_digest(expected, sig):
        raise HTTPException(403, "Invalid GitHub signature.")
    return sig,secret


def signed_event(raw, headers, config, current, signature):
    sig, secret = signature
    try:
        data = json.loads(raw)
        if config.get("installation_id") and str(data.get("installation",{}).get("id")) != str(config["installation_id"]):
            raise HTTPException(403, "Event belongs to a different GitHub installation.")
        repo = current["product_repo"]
        if data["repository"]["full_name"] != repo:
            raise HTTPException(403, "Repository outside the configured scope.")
        kind = headers.get("x-github-event")
        delivery = headers.get("x-github-delivery", "")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", delivery):
            raise HTTPException(422, "Invalid delivery identifier.")
        if kind == "pull_request":
            pr = data.get("pull_request", {})
            if (
                data.get("action") != "closed"
                or not pr.get("merged")
                or pr["base"]["ref"] != current["source_branch"]
            ):
                return None
            event = github_event(raw, sig, secret, repo, delivery)
        elif kind == "push":
            if data.get("deleted") or data["ref"] != "refs/heads/" + current["source_branch"]:
                return None
            paths = sorted(
                {
                    p
                    for c in data.get("commits", [])
                    for k in ("added", "modified", "removed")
                    for p in c.get(k, [])
                }
            )
            event = dict(
                source="github",
                repository=repo,
                title="Review changes to " + repo,
                text="Inspect the changed revision and recapture affected journeys.",
                revision=data["after"],
                changed_paths=paths[:200],
                paths_incomplete=len(paths) > 200 or len(data.get("commits", [])) >= 2048,
            )
        else:
            return None
        sha = event["revision"]
        if not re.fullmatch("[0-9a-f]{40}|[0-9a-f]{64}", sha):
            raise ValueError
        event.update(
            id="github:" + repo + "@" + sha,
            source_url=f"https://github.com/{repo}/commit/{sha}",
            requires_capture=True,
            agent_questions=["Which journeys are affected at the deployed revision?"],
        )
        return delivery, event
    except (TypeError, KeyError, ValueError, AttributeError):
        raise HTTPException(422, "Malformed GitHub event.") from None


class BoundConnection:
    def __init__(self, db):
        self.db = db

    def connection(self):
        return nullcontext(self.db)


def receive(pool, org, project, raw, headers):
    config = binding(org, project)
    signature=verify_signature(raw,headers,config)
    # Authenticate before allocating or modifying workspace state.
    with pool.connection() as db:
        current = setup(db, org, project)
        if not current["connected"]:
            raise HTTPException(409, "GitHub intake is disconnected.")
        normalized = signed_event(raw, headers, config, current, signature)
        if not normalized:
            return {"status": "ignored"}
        delivery, event = normalized
        key = (org, project)
        digest = hashlib.sha256(raw).hexdigest()
        old = db.execute(
            "SELECT payload_hash,item_id FROM docs_source_deliveries WHERE organization_id=%s AND project_id=%s AND delivery=%s",
            (*key, delivery),
        ).fetchone()
        if old:
            if old[0] != digest:
                raise HTTPException(409, "Delivery identifier reused with different content.")
            return {"status": "duplicate", "item_id": old[1]}
        prior = db.execute(
            "SELECT item_id FROM docs_source_deliveries WHERE organization_id=%s AND project_id=%s AND repository=%s AND revision=%s LIMIT 1",
            (*key, event["repository"], event["revision"]),
        ).fetchone()
        if prior:
            item_id = prior[0]
        else:
            store = PostgresStore(BoundConnection(db), org)
            item_id = store.ingest(project, current["connected_by"], event)["item_id"]
        db.execute(
            "INSERT INTO docs_source_deliveries(organization_id,project_id,delivery,payload_hash,repository,revision,item_id,destination) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                *key,
                delivery,
                digest,
                event["repository"],
                event["revision"],
                item_id,
                Jsonb({k: current[k] for k in ("docs_repo", "branch", "docs_root")}),
            ),
        )
        from .refresh import record
        record(db,org,project,event,item_id)
        return {
            "status": "duplicate" if prior else "received",
            "item_id": item_id,
            "source_revision": event["revision"],
            "deployed_revision": None,
        }


def router(pool, auth):
    routes = APIRouter()

    @routes.get(PREFIX + "/github/repos")
    def list_repos(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            setup(db, org, project)
        return repositories(github_access(binding(org, project)))

    @routes.post(PREFIX + "/github/connect")
    def connect(org: str, project: str, body: Scope, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            expect_revision(setup(db, org, project), body.revision)
        if body.docs_root and (
            not re.fullmatch(r"[\w./-]+", body.docs_root)
            or any(p.lower() in ("", ".", "..", ".git", ".github") for p in body.docs_root.split("/"))
            or PurePosixPath(body.docs_root).is_absolute()
        ):
            raise HTTPException(
                422, "Use a relative docs directory or leave it blank for the repository root."
            )
        config = github_access(binding(org, project))
        available = repositories(config)
        if body.product_repo not in available or body.docs_repo not in available:
            raise HTTPException(403, "Select repositories visible to this installation.")
        github_get(config, "/repos/" + body.docs_repo + "/branches/" + quote(body.branch, safe=""))
        if len(config.get("webhook_secret", "")) < 24:
            raise HTTPException(503, "Configure the webhook signing secret.")
        with pool.connection() as db:
            admin(db, org, actor)
            expect_revision(setup(db, org, project), body.revision)
            db.execute(
                """UPDATE docs_setup SET product_repo=%s,docs_repo=%s,branch=%s,docs_root=%s,source_branch=%s,
                connected=true,connected_by=%s,revision=revision+1 WHERE organization_id=%s AND project_id=%s""",
                (
                    body.product_repo,
                    body.docs_repo,
                    body.branch,
                    body.docs_root,
                    available[body.product_repo],
                    actor,
                    org,
                    project,
                ),
            )
        return {"connected": True}

    @routes.post(PREFIX + "/github/disconnect")
    def disconnect(org: str, project: str, body: Version, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            expect_revision(setup(db, org, project), body.revision)
            db.execute(
                "UPDATE docs_setup SET connected=false,revision=revision+1 WHERE organization_id=%s AND project_id=%s",
                (org, project),
            )
        return {"connected": False}

    @routes.post(PREFIX + "/github/webhook")
    async def webhook(org: str, project: str, request: Request):
        return await run_in_threadpool(
            receive, pool, org, project, await request.body(), request.headers
        )

    return routes
