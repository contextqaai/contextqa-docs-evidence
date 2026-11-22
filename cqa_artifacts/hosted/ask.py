"""Project-scoped retrieval. A reader key can only use the citation search route."""

import hashlib
import secrets
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from .onboarding import PREFIX
from .store import PostgresStore
from .github_intake import BoundConnection


class Query(BaseModel):
    question: str = Field(min_length=2, max_length=400)


class Label(BaseModel):
    label: str = Field(min_length=1, max_length=100)


class Proposal(BaseModel):
    request_id: UUID
    source_item: str
    goal: str = Field(min_length=3, max_length=200)


def search(db, org, project, actor, question):
    state = PostgresStore(BoundConnection(db), org).snapshot(project, actor)
    tokens = {w.lower() for w in question.split() if len(w) > 2}
    rows = []

    def append(title, body, cite, kind):
        matches = [
            line.strip()
            for line in body.splitlines()
            if any(w in line.lower() for w in tokens)
        ]
        score = sum(w in (title + " " + body).lower() for w in tokens)
        if score and len(rows) < 4000:
            rows.append(
                dict(
                    score=score,
                    title=title,
                    excerpt=(matches[0] if matches else body)[:400],
                    citation=cite,
                    kind=kind,
                )
            )

    if state["role"] != "contributor":
        for path, digest, body in db.execute(
            """SELECT h.path,h.digest,v.body FROM docs_guide_heads h JOIN docs_guide_versions v USING(organization_id,project_id,path,digest)
           WHERE h.organization_id=%s AND h.project_id=%s""",
            (org, project),
        ):
            append(path, body, {"path": path, "version": digest}, "reviewed guide")
    for item in state["items"].values():
        if item["status"] == "archived":
            continue
        for c in item["changes"]:
            append(
                item["title"],
                c["after"],
                {"item": item["id"], "article": c["path"], "revision": item["version"]},
                "review request",
            )
    return {"results": sorted(rows, key=lambda r: (-r["score"], r["title"]))[:20]}


def router(pool, auth):
    r = APIRouter()

    @r.post(PREFIX + "/ask")
    def ask(org: str, project: str, body: Query, actor=Depends(auth)):
        with pool.connection() as db:
            return search(db, org, project, actor, body.question)

    @r.post(PREFIX + "/ask/propose")
    def propose(org: str, project: str, body: Proposal, actor=Depends(auth)):
        with pool.connection() as db:
            store = PostgresStore(BoundConnection(db), org)
            value = store.snapshot(project, actor)
            if value["role"] == "contributor":
                raise HTTPException(403, "An editor must propose new work.")
            source = store.get_item(value, body.source_item)
            event = value["events"][source["event_id"]]["event"]
            return store.ingest(
                project,
                actor,
                dict(
                    id="ask:" + str(body.request_id),
                    source="manual",
                    title=body.goal,
                    text="Follow up on " + source["title"] + ". " + body.goal,
                    source_url=event.get("source_url"),
                    related_request=source["id"],
                ),
            )

    @r.post(PREFIX + "/ask/keys")
    def grant(org: str, project: str, body: Label, actor=Depends(auth)):
        with pool.connection() as db:
            PostgresStore(BoundConnection(db), org).snapshot(project, actor)
            db.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (org + "/" + project + "/" + actor,),
            )
            prior = db.execute(
                """SELECT count(*) FROM docs_reader_keys WHERE organization_id=%s AND project_id=%s AND subject=%s
                AND revoked_at IS NULL AND expires_at>now()""",
                (org, project, actor),
            ).fetchone()[0]
            if prior >= 5:
                raise HTTPException(409, "Revoke an existing reader key first.")
            key = secrets.token_urlsafe(32)
            ident = uuid4()
            db.execute(
                """INSERT INTO docs_reader_keys(id,organization_id,project_id,subject,digest,label,expires_at)
                VALUES(%s,%s,%s,%s,%s,%s,now()+interval '30 days')""",
                (
                    ident,
                    org,
                    project,
                    actor,
                    hashlib.sha256(key.encode()).hexdigest(),
                    body.label,
                ),
            )
            return {"id": ident, "key": key}

    @r.get(PREFIX + "/ask/keys")
    def keys(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            PostgresStore(BoundConnection(db), org).snapshot(project, actor)
            return [
                dict(id=i, label=l, expires_at=e)
                for i, l, e in db.execute(
                    """SELECT id,label,expires_at FROM docs_reader_keys
                WHERE organization_id=%s AND project_id=%s AND subject=%s AND revoked_at IS NULL AND expires_at>now()""",
                    (org, project, actor),
                )
            ]

    @r.post(PREFIX + "/ask/keys/{ident}/revoke")
    def revoke(org: str, project: str, ident: UUID, actor=Depends(auth)):
        with pool.connection() as db:
            db.execute(
                "UPDATE docs_reader_keys SET revoked_at=now() WHERE id=%s AND organization_id=%s AND project_id=%s AND subject=%s",
                (ident, org, project, actor),
            )
        return {"revoked": True}

    @r.post("/api/assistant/search")
    def external(body: Query, authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Reader key required.")
        digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
        with pool.connection() as db:
            row = db.execute(
                "SELECT organization_id,project_id,subject FROM docs_reader_keys WHERE digest=%s AND revoked_at IS NULL AND expires_at>now() FOR SHARE",
                (digest,),
            ).fetchone()
            if not row:
                raise HTTPException(401, "Reader key expired or revoked.")
            return search(db, *row, body.question)

    return r
