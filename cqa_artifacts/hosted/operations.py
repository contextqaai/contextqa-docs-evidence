"""Workspace operations, scoped delivery reconciliation and static OpenAPI import."""

from pathlib import Path
import re
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .. import core
from ..loop import fingerprint, path_name
from .onboarding import PREFIX, admin, binding, setup
from .github_intake import github_get, BoundConnection
from .library import scope
from .store import PostgresStore


class ApiImport(BaseModel):
    path: str
    spec: dict
    reference: str = Field(max_length=500)


class Delivery(BaseModel):
    item: str
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirm: bool


def reference_page(spec):
    if not re.fullmatch(r"3\.\d+\.\d+", str(spec.get("openapi", ""))):
        raise core.Rejected("Use an OpenAPI 3 JSON document.")
    paths = spec.get("paths")
    if not isinstance(paths, dict) or not paths or len(paths) > 300:
        raise core.Rejected("Provide between one and 300 API paths.")
    lines = []
    skipped = []
    for url, methods in sorted(paths.items()):
        if not isinstance(methods, dict) or not url.startswith("/") or len(url) > 500:
            skipped.append(url[:100])
            continue
        for method, op in sorted(methods.items()):
            if method.upper() not in (
                "GET",
                "PUT",
                "POST",
                "PATCH",
                "DELETE",
                "HEAD",
                "OPTIONS",
                "TRACE",
            ) or not isinstance(op, dict):
                skipped.append(url + " " + method)
                continue
            lines.extend(
                [
                    "## " + method.upper() + " " + core.markdown_plain(url),
                    "",
                    core.markdown_plain(
                        str(
                            op.get("summary")
                            or op.get("operationId")
                            or "See the operation in the source specification."
                        )[:1000]
                    ),
                    "",
                ]
            )
    if not lines:
        raise core.Rejected("No supported operations were found.")
    title = (
        spec.get("info", {}).get("title", "API reference")
        if isinstance(spec.get("info"), dict)
        else "API reference"
    )
    return "# " + core.markdown_plain(str(title)) + "\n\n" + "\n".join(lines), skipped


def router(pool, auth):
    r = APIRouter()

    @r.get(PREFIX + "/operations")
    def overview(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            role = scope(db, org, project, actor)
            cfg = setup(db, org, project)
            groups = {}
            for name, table in (
                ("workflows", "docs_runs"),
                ("captures", "docs_capture_jobs"),
                ("pull_requests", "docs_guide_prs"),
            ):
                groups[name] = dict(
                    db.execute(
                        "SELECT status,count(*) FROM "
                        + table
                        + " WHERE organization_id=%s AND project_id=%s GROUP BY status",
                        (org, project),
                    ).fetchall()
                )
            refresh = db.execute(
                """SELECT r.path,r.revision,r.item_id,r.journeys,r.base=h.digest,r.created_at,r.status,r.reason,r.proposal FROM docs_refresh_requests r
                JOIN docs_guide_heads h USING(organization_id,project_id,path) WHERE r.organization_id=%s AND r.project_id=%s ORDER BY r.created_at DESC LIMIT 100""",
                (org, project),
            ).fetchall()
            prs = db.execute(
                """SELECT item_id,status,pr_url FROM docs_guide_prs WHERE organization_id=%s AND project_id=%s ORDER BY item_id LIMIT 100""",
                (org, project),
            ).fetchall()
            phases = db.execute(
                "SELECT item_id,phase,commit_sha,result->>'successful' FROM docs_publication_checks WHERE organization_id=%s AND project_id=%s ORDER BY checked_at",
                (org, project),
            ).fetchall()
            media = db.execute(
                "SELECT count(*),coalesce(sum(octet_length(content)),0) FROM docs_guide_media WHERE organization_id=%s AND project_id=%s",
                (org, project),
            ).fetchone()
            return dict(
                groups=groups,
                role=role,
                repo=cfg["docs_repo"],
                branch=cfg["branch"],
                root=cfg["docs_root"],
                connected=cfg["connected"],
                media_files=media[0],
                media_bytes=media[1],
                refresh=[
                    dict(
                        path=p,
                        revision=v,
                        item=i,
                        journeys=j,
                        base_current=b,
                        created_at=t,
                        status=s,
                        reason=why,
                        proposal=proposal,
                    )
                    for p, v, i, j, b, t, s, why, proposal in refresh
                ],
                phases=[
                    dict(item=i, phase=p, revision=sha, successful=success)
                    for i, p, sha, success in phases
                ],
                deliveries=[dict(item=i, status=s, url=u) for i, s, u in prs],
            )

    @r.post(PREFIX + "/operations/draft-pr")
    def draft_pr(org: str, project: str, body: Delivery, actor=Depends(auth)):
        from .guide_intake import deliver_guide

        with pool.connection() as db:
            admin(db, org, actor)
        cfg = binding(org, project)
        if not cfg.get("documentation_checkout") or not cfg.get(
            "delivery_journal_directory"
        ):
            raise core.Rejected(
                "Configure the workspace documentation checkout and delivery journal."
            )
        return deliver_guide(
            pool,
            org,
            project,
            actor,
            body.item,
            Path(cfg["documentation_checkout"]),
            body.base_sha,
            Path(cfg["delivery_journal_directory"]),
            body.confirm,
        )

    @r.post(PREFIX + "/operations/reconcile/{item}")
    def reconcile(org: str, project: str, item: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg = setup(db, org, project)
            rows = db.execute(
                "SELECT approval_digest,status,pr_url FROM docs_guide_prs WHERE organization_id=%s AND project_id=%s AND item_id=%s FOR UPDATE",
                (org, project, item),
            ).fetchall()
            if len(rows) != 1 or not cfg["connected"]:
                raise core.Rejected(
                    "Select one delivery attempt in a connected workspace."
                )
            digest, status, pr_url = rows[0]
            repo = cfg["docs_repo"]
            branch = "contextqa-docs/" + item + "-" + digest[:12]
            prs = github_get(
                binding(org, project),
                "/repos/" + repo + "/pulls",
                {
                    "head": repo.split("/")[0] + ":" + branch,
                    "base": cfg["branch"],
                    "state": "all",
                },
            )
            matches = [
                p
                for p in prs
                if p.get("head", {}).get("ref") == branch
                and (p["head"].get("repo") or {}).get("full_name") == repo
                and p.get("base", {}).get("ref") == cfg["branch"]
            ]
            if len(matches) != 1:
                raise core.Rejected(
                    "No unique matching pull request was found. The existing attempt is preserved."
                )
            pr = matches[0]
            url = "https://github.com/" + repo + "/pull/" + str(int(pr["number"]))
            if pr_url and url != pr_url:
                raise core.Rejected("The provider returned a different pull request.")
            status = (
                "merged"
                if pr.get("merged_at")
                else "closed"
                if pr.get("state") == "closed"
                else "draft_pr_created"
            )
            db.execute(
                "UPDATE docs_guide_prs SET status=%s,pr_url=%s WHERE organization_id=%s AND project_id=%s AND item_id=%s AND approval_digest=%s",
                (status, url, org, project, item, digest),
            )
            if status == "merged":
                from .publication import record

                record(
                    db,
                    (org, project, item, digest),
                    "merge",
                    pr.get("merge_commit_sha"),
                    {"pull_request": url},
                )
            return dict(
                status=status,
                url=url,
                merge_sha=pr.get("merge_commit_sha") if status == "merged" else None,
                site_verified=False,
            )

    @r.post(PREFIX + "/operations/import-api")
    def api_import(org: str, project: str, body: ApiImport, actor=Depends(auth)):
        path = path_name(body.path)
        from ..guides import url

        url(body.reference)
        md, skipped = reference_page(body.spec)
        with pool.connection() as db:
            scope(db, org, project, actor, True)
            store = PostgresStore(BoundConnection(db), org)
            state = store.snapshot(project, actor)
            before = state["articles"].get(path, {}).get("body", "")
            if before == md:
                return dict(status="no_change", skipped=skipped)
            spec_digest = fingerprint(body.spec)
            event = dict(
                id="openapi:"
                + fingerprint([path, spec_digest, body.reference, fingerprint(before)]),
                source="manual",
                title="Review API reference",
                source_url=body.reference,
                text="Generated from OpenAPI "
                + str(body.spec["openapi"])
                + ". Review the source specification and capture reader-facing examples.",
                spec_digest=spec_digest,
                requires_screenshots=True,
                edits=[
                    dict(
                        path=path,
                        before=before,
                        after=md,
                        reason="Updated API specification",
                    )
                ],
            )
            return dict(
                **store.ingest(project, actor, event),
                status="awaiting_review",
                skipped=skipped,
            )

    return r
