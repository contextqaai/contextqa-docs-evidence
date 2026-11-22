"""Separate merge, successful build and live article/media receipts."""

import hashlib
import hmac
import re
from urllib.parse import quote, urlsplit
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from .. import core
from .library import edition, scope
from .onboarding import PREFIX, binding, admin, setup


def record(db, key, phase, sha, value):
    if not re.fullmatch(r"[a-f0-9]{40}", sha or ""):
        raise core.Rejected("A full merged commit is required.")
    db.execute(
        """INSERT INTO docs_publication_checks(organization_id,project_id,item_id,approval_digest,phase,commit_sha,result)
        VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(organization_id,project_id,item_id,approval_digest,phase)
        DO UPDATE SET result=excluded.result,checked_at=now() WHERE docs_publication_checks.commit_sha=excluded.commit_sha""",
        (*key, phase, sha, Jsonb(value)),
    )


class Build(BaseModel):
    item: str
    approval: str = Field(pattern="^[0-9a-f]{64}$")
    repository: str
    commit: str = Field(pattern="^[0-9a-f]{40}$")
    successful: bool
    build_id: str = Field(min_length=1, max_length=150)


def fetch_public(url, expected):
    with httpx.stream(
        "GET",
        url,
        timeout=15,
        follow_redirects=False,
        headers={"accept-encoding": "identity"},
    ) as res:
        if res.status_code != 200:
            raise core.Rejected("The live site did not return the expected file.")
        digest = hashlib.sha256()
        size = 0
        for block in res.iter_bytes(65536):
            size += len(block)
            if size > 16 * 1024 * 1024:
                raise core.Rejected("Live file exceeds the verification limit.")
            digest.update(block)
        if digest.hexdigest() != expected:
            raise core.Rejected("Live content differs from the approved version.")


def router(pool, auth):
    r = APIRouter()

    @r.post(PREFIX + "/publication/build")
    async def build(org: str, project: str, request: Request):
        raw = await request.body()
        cfg = binding(org, project)
        secret = cfg.get("publication_webhook_secret")
        signature = request.headers.get("x-docs-signature", "")
        if not secret or not hmac.compare_digest(
            signature,
            "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(),
        ):
            raise HTTPException(401, "Build signature required.")
        try:
            body = Build.model_validate_json(raw)
        except ValueError:
            raise HTTPException(422, "Invalid build receipt.") from None
        key = (org, project, body.item, body.approval)
        with pool.connection() as db:
            dest = setup(db, org, project)
            merge = db.execute(
                """SELECT commit_sha FROM docs_publication_checks WHERE organization_id=%s AND project_id=%s AND item_id=%s AND approval_digest=%s AND phase='merge'""",
                key,
            ).fetchone()
            if (
                not dest["connected"]
                or dest["docs_repo"] != body.repository
                or not merge
                or merge[0] != body.commit
            ):
                raise core.Rejected(
                    "Confirm this repository's merged pull request before recording its build."
                )
            record(
                db,
                key,
                "build",
                body.commit,
                {"successful": body.successful, "build_id": body.build_id},
            )
            if not body.successful:
                db.execute(
                    "DELETE FROM docs_publication_checks WHERE organization_id=%s AND project_id=%s AND item_id=%s AND approval_digest=%s AND phase='live'",
                    key,
                )
        return {"recorded": True}

    @r.post(PREFIX + "/publication/{item}/verify")
    def verify(org: str, project: str, item: str, actor=Depends(auth)):
        cfg = binding(org, project)
        origin = cfg.get("published_markdown_origin", "").rstrip("/")
        u = urlsplit(origin)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.query
            or u.fragment
        ):
            raise core.Rejected(
                "Configure the trusted HTTPS Markdown and evidence origin."
            )
        def release(db):
            rows = db.execute(
                """SELECT b.approval_digest,b.commit_sha,s.versions FROM docs_publication_checks b JOIN docs_library_saves s
                ON s.organization_id=b.organization_id AND s.project_id=b.project_id AND s.item_id=b.item_id AND s.approval=b.approval_digest
                WHERE b.organization_id=%s AND b.project_id=%s AND b.item_id=%s AND b.phase='build' AND b.result->>'successful'='true'
                AND NOT EXISTS (
                    SELECT FROM jsonb_each_text(s.versions) v(path, digest)
                    LEFT JOIN docs_guide_heads h ON h.organization_id=b.organization_id AND h.project_id=b.project_id AND h.path=v.path
                    WHERE h.digest IS DISTINCT FROM v.digest
                ) FOR SHARE OF b,s""",
                (org, project, item),
            ).fetchall()
            if len(rows) != 1:
                raise core.Rejected(
                    "Save the approved version and verify the successful build first."
                )
            return rows[0]

        with pool.connection() as db:
            admin(db, org, actor)
            approval, sha, versions = release(db)
            files = {}
            for path, digest in versions.items():
                v = edition(db, org, project, path, digest)
                files[path] = core.digest(v["body"].encode())
                for m in v["media"]:
                    files[m["path"]] = m["digest"]
            if len(files) > 80:
                raise core.Rejected("Review this release in smaller batches.")
        try:
            for path, digest in files.items():
                fetch_public(origin + "/" + quote(path, safe="/"), digest)
        except httpx.HTTPError:
            raise core.Rejected(
                "Live verification did not complete. Retry after the site is available."
            ) from None
        with pool.connection() as db:
            admin(db, org, actor)
            if release(db) != (approval, sha, versions) or binding(org, project).get(
                "published_markdown_origin", ""
            ).rstrip("/") != origin:
                raise core.Rejected("The release changed during verification. Retry with the current version.")
            record(
                db,
                (org, project, item, approval),
                "live",
                sha,
                {"files": files, "origin": origin},
            )
            return {"status": "live_verified", "files": len(files), "commit": sha}

    @r.get(PREFIX + "/reader/markdown")
    def markdown(org: str, project: str, path: str, version: str, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor)
            return Response(
                edition(db, org, project, path, version)["body"],
                media_type="text/markdown",
            )

    @r.get(PREFIX + "/reader/llms.txt")
    def index(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor)
            rows = db.execute(
                "SELECT path,digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s ORDER BY path",
                (org, project),
            )
            from urllib.parse import urlencode

            body = "# Reviewed documentation\n\n" + "\n".join(
                "- ["
                + core.markdown_plain(p)
                + "](markdown?"
                + urlencode({"path": p, "version": d})
                + ")"
                for p, d in rows
            )
            return Response(body, media_type="text/plain")

    return r
