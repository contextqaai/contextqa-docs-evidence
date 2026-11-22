"""Authenticated workspace setup, invitations and tenant-bound integration configuration."""

import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field
from typing import Literal

from ..loop import validate_manifest

Role = Literal["admin", "editor", "contributor"]
SLUG = r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
PREFIX = "/api/orgs/{org}/projects/{project}"


class NewWorkspace(BaseModel):
    request_id: UUID
    name: str = Field(default="", max_length=120)
    app_url: str = Field(max_length=2048)


class SetupEdit(BaseModel):
    revision: int = Field(ge=0)
    app_url: str = Field(max_length=2048)
    description: str = Field(min_length=1, max_length=600)


class Invite(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    role: Role


class MemberEdit(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    role: Literal["admin", "editor", "contributor", "remove"]


class AcceptInvite(BaseModel):
    token: str = Field(min_length=20, max_length=160)


def app_address(value):
    try:
        url = urlsplit(value)
        if (
            url.scheme == "https"
            and url.hostname
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and not re.search(r"[\s\\]", value)
        ):
            return value
    except ValueError:
        pass
    raise HTTPException(422, "Enter an HTTPS app URL without embedded credentials, query or fragment.")


def binding(org, project):
    """Trusted deployment file. No workspace-supplied token references or arbitrary origins."""
    filename = os.getenv("DOCS_CONNECTIONS_FILE")
    if not filename:
        return {}
    try:
        return json.loads(Path(filename).read_text()).get(org + "/" + project, {})
    except (ValueError, OSError):
        raise HTTPException(503, "Workspace connection configuration unavailable.") from None


def admin(db, org, actor):
    # Serialize membership changes, including two admins trying to remove each other.
    db.execute("SELECT id FROM docs_organizations WHERE id=%s FOR UPDATE", (org,))
    row = db.execute(
        "SELECT role FROM docs_memberships WHERE organization_id=%s AND subject=%s", (org, actor)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Workspace unavailable")
    if row[0] != "admin":
        raise HTTPException(403, "Organization administrator required")


def setup(db, org, project):
    row = db.execute(
        "SELECT state->'manifest'->>'application_url' FROM docs_projects WHERE organization_id=%s AND id=%s FOR UPDATE",
        (org, project),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Project unavailable")
    db.execute(
        "INSERT INTO docs_setup(organization_id,project_id,app_url) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
        (org, project, row[0]),
    )
    with db.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT * FROM docs_setup WHERE organization_id=%s AND project_id=%s", (org, project)
        ).fetchone()


def expect_revision(current, revision):
    if current["revision"] != revision:
        raise HTTPException(409, "Setup changed. Reload the saved configuration before continuing.")


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def router(pool, auth):
    routes = APIRouter()

    @routes.post("/api/workspaces")
    def create(body: NewWorkspace, actor=Depends(auth)):
        url = app_address(body.app_url)
        org = "ws-" + uuid5(NAMESPACE_URL, json.dumps([actor, str(body.request_id)])).hex
        manifest = validate_manifest(
            dict(
                schema=1,
                project_id="docs",
                name=body.name.strip() or urlsplit(url).hostname,
                repository="Unconfigured",
                application_url=url,
                environment="Deployment not verified",
                instructions="Use verified ContextQA journeys and editor review.",
                sections=[
                    dict(
                        id="start",
                        path="guides/getting-started.md",
                        title="Getting started",
                        owner=actor,
                    )
                ],
            )
        )
        state = dict(manifest=manifest, members={}, articles={}, events={}, items={}, audit=[])
        with pool.connection() as db:
            added = db.execute(
                "INSERT INTO docs_organizations(id,name) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING id",
                (org, manifest["name"]),
            ).fetchone()
            if added:
                db.execute("INSERT INTO docs_memberships VALUES(%s,%s,'admin')", (org, actor))
                db.execute(
                    "INSERT INTO docs_projects(organization_id,id,state) VALUES(%s,'docs',%s)",
                    (org, Jsonb(state)),
                )
                db.execute("INSERT INTO docs_setup(organization_id,project_id,app_url,description) VALUES(%s,'docs',%s,%s)",
                           (org,url,"Discover the main tasks available to this account and capture evidence for task-based guides."))
            else:
                admin(db, org, actor)
        return dict(workspace=org + "/docs")

    @routes.get(PREFIX + "/setup")
    def read(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            current = setup(db, org, project)
            with db.cursor(row_factory=dict_row) as cur:
                for key, sql, args in [
                    (
                        "members",
                        "SELECT subject,role FROM docs_memberships WHERE organization_id=%s ORDER BY subject",
                        (org,),
                    ),
                    (
                        "invites",
                        "SELECT subject,role,expires_at FROM docs_invites WHERE organization_id=%s ORDER BY subject",
                        (org,),
                    ),
                    (
                        "discoveries",
                        "SELECT id,status,provider_job,setup_revision,evidence_receipt FROM docs_discoveries WHERE organization_id=%s AND project_id=%s ORDER BY created_at DESC LIMIT 15",
                        (org, project),
                    ),
                    (
                        "pull_requests",
                        "SELECT item_id,status,pr_url FROM docs_guide_prs WHERE organization_id=%s AND project_id=%s ORDER BY created_at DESC LIMIT 15",
                        (org, project),
                    ),
                    (
                        "deliveries",
                        "SELECT delivery,repository,revision,item_id,received_at FROM docs_source_deliveries WHERE organization_id=%s AND project_id=%s ORDER BY received_at DESC LIMIT 15",
                        (org, project),
                    ),
                ]:
                    current[key] = cur.execute(sql, args).fetchall()
        return current

    @routes.post(PREFIX + "/setup")
    def save(org: str, project: str, body: SetupEdit, actor=Depends(auth)):
        url = app_address(body.app_url)
        with pool.connection() as db:
            admin(db, org, actor)
            current = setup(db, org, project)
            expect_revision(current, body.revision)
            if (current["app_url"], current["description"]) != (url, body.description):
                db.execute(
                    "UPDATE docs_setup SET app_url=%s,description=%s,revision=revision+1 WHERE organization_id=%s AND project_id=%s",
                    (url, body.description, org, project),
                )
                db.execute(
                    "UPDATE docs_projects SET state=jsonb_set(state,'{manifest,application_url}',to_jsonb(%s::text)) WHERE organization_id=%s AND id=%s",
                    (url, org, project),
                )
        return {"saved": True}

    @routes.post("/api/orgs/{org}/invites")
    def invite(org: str, body: Invite, actor=Depends(auth)):
        token = secrets.token_urlsafe(32)
        with pool.connection() as db:
            admin(db, org, actor)
            if db.execute(
                "SELECT 1 FROM docs_memberships WHERE organization_id=%s AND subject=%s",
                (org, body.subject),
            ).fetchone():
                raise HTTPException(409, "This account is already a member.")
            db.execute(
                """INSERT INTO docs_invites VALUES(%s,%s,%s,%s,now()+interval '7 days')
                ON CONFLICT(organization_id,subject) DO UPDATE SET role=EXCLUDED.role,digest=EXCLUDED.digest,expires_at=EXCLUDED.expires_at""",
                (org, body.subject, body.role, token_hash(token)),
            )
        return {"token": token}

    @routes.post("/api/invites/accept")
    def accept(body: AcceptInvite, actor=Depends(auth)):
        digest = token_hash(body.token)
        with pool.connection() as db:
            row = db.execute(
                "SELECT organization_id FROM docs_invites WHERE subject=%s AND digest=%s",
                (actor, digest),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Invitation unavailable for this account.")
            org = row[0]
            db.execute("SELECT id FROM docs_organizations WHERE id=%s FOR UPDATE", (org,))
            inv = db.execute(
                "SELECT role,expires_at>now() FROM docs_invites WHERE organization_id=%s AND subject=%s AND digest=%s FOR UPDATE",
                (org, actor, digest),
            ).fetchone()
            if not inv:
                raise HTTPException(404, "Invitation already used or replaced.")
            if not inv[1]:
                raise HTTPException(410, "Invitation expired. Ask your administrator for a new code.")
            db.execute(
                "INSERT INTO docs_memberships VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (org, actor, inv[0]),
            )
            db.execute("DELETE FROM docs_invites WHERE digest=%s", (digest,))
        return {"organization_id": org}

    @routes.post("/api/orgs/{org}/members")
    def member(org: str, body: MemberEdit, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            old = db.execute(
                "SELECT role FROM docs_memberships WHERE organization_id=%s AND subject=%s",
                (org, body.subject),
            ).fetchone()
            if not old:
                raise HTTPException(404, "Member unavailable")
            if old[0] == "admin" and body.role != "admin":
                count = db.execute(
                    "SELECT count(*) FROM docs_memberships WHERE organization_id=%s AND role='admin'",
                    (org,),
                ).fetchone()[0]
                if count == 1:
                    raise HTTPException(409, "Keep at least one active administrator.")
            if body.role == "remove":
                db.execute(
                    "DELETE FROM docs_memberships WHERE organization_id=%s AND subject=%s",
                    (org, body.subject),
                )
            else:
                db.execute(
                    "UPDATE docs_memberships SET role=%s WHERE organization_id=%s AND subject=%s",
                    (body.role, org, body.subject),
                )
        return {"saved": True}

    return routes
