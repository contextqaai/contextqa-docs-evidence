"""Authenticated guide versions, linked media and derived enablement drafts."""

import base64
import difflib
import mimetypes
from typing import Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from .. import core
from ..editions import checked_media
from ..loop import fingerprint, path_name
from .github_intake import BoundConnection
from .onboarding import PREFIX
from .store import PostgresStore


class Release(BaseModel):
    item: str
    version: int
    expected_heads: dict[str, str | None]


class AssetDraft(BaseModel):
    path: str
    digest: str
    audience: str = Field(min_length=1, max_length=120)
    format: Literal["Training lesson", "Release note"]


class AssetDecision(BaseModel):
    version: int
    action: Literal["save", "approve", "export", "refresh"]
    body: str | None = Field(default=None, max_length=100000)


def scope(db, org, project, actor, editor=False):
    row = db.execute(
        """SELECT m.role FROM docs_memberships m JOIN docs_projects p ON p.organization_id=m.organization_id
                     WHERE m.organization_id=%s AND p.id=%s AND m.subject=%s""",
        (org, project, actor),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Workspace unavailable.")
    if row[0] not in ("admin", "editor"):
        raise HTTPException(403, "Editor access required for the guide library.")
    return row[0]


def edition(db, org, project, path, digest):
    row = db.execute(
        """SELECT body,media,source,parent,item_id,actor,created_at FROM docs_guide_versions
        WHERE organization_id=%s AND project_id=%s AND path=%s AND digest=%s""",
        (org, project, path, digest),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Guide version unavailable.")
    return dict(
        zip(("body", "media", "source", "parent", "item", "actor", "created_at"), row)
    )


def router(pool, auth):
    routes = APIRouter()
    base = PREFIX + "/library"

    @routes.get(base)
    def index(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor)
            rows = db.execute(
                """SELECT v.path,v.digest,v.item_id,v.created_at,v.media,coalesce(h.digest=v.digest,false) FROM docs_guide_versions v
                LEFT JOIN docs_guide_heads h USING(organization_id,project_id,path)
                WHERE v.organization_id=%s AND v.project_id=%s ORDER BY v.created_at DESC,v.path""",
                (org, project),
            ).fetchall()
            assets = db.execute(
                """SELECT a.id,a.path,a.digest,a.audience,a.format,a.body,a.version,a.status,a.owner_id,a.exported_at,h.digest IS DISTINCT FROM a.digest
                FROM docs_enablement a LEFT JOIN docs_guide_heads h USING(organization_id,project_id,path)
                WHERE a.organization_id=%s AND a.project_id=%s ORDER BY a.path,a.format""",
                (org, project),
            ).fetchall()
            return dict(
                versions=[
                    dict(
                        zip(
                            (
                                "path",
                                "digest",
                                "item",
                                "created_at",
                                "media",
                                "current",
                            ),
                            r,
                        )
                    )
                    for r in rows
                ],
                assets=[
                    dict(
                        zip(
                            (
                                "id",
                                "path",
                                "digest",
                                "audience",
                                "format",
                                "body",
                                "version",
                                "status",
                                "owner",
                                "exported_at",
                                "stale",
                            ),
                            a,
                        )
                    )
                    for a in assets
                ],
            )

    @routes.post(base + "/save")
    def save(org: str, project: str, body: Release, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor, True)
            store = PostgresStore(BoundConnection(db), org)
            with store.transaction(project) as state:
                item = store.get_item(state, body.item)
                event = state["events"][item["event_id"]]["event"]
                if not item.get("approval") or item["approval"][
                    "digest"
                ] != fingerprint(store.approval_payload(state, item)):
                    raise core.Rejected(
                        "Approve the current guide and its media first."
                    )
                approval = item["approval"]["digest"]
                # A lost response can be replayed even after the bundle increments the request version.
                prior = db.execute(
                    "SELECT versions FROM docs_library_saves WHERE organization_id=%s AND project_id=%s AND item_id=%s AND approval=%s",
                    (org, project, body.item, approval),
                ).fetchone()
                if prior:
                    return dict(status="recorded", versions=prior[0])
                if item["version"] != body.version:
                    raise core.Rejected("Review changed. Reload this request.")
                pages = checked_media(item, event)
                if set(body.expected_heads) != set(pages):
                    raise core.Rejected(
                        "Provide the reviewed baseline for every accepted article."
                    )
                heads = dict(
                    db.execute(
                        "SELECT path,digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s",
                        (org, project),
                    ).fetchall()
                )
                aliases = {
                    r[0]
                    for r in db.execute(
                        "SELECT source FROM docs_reader_redirects WHERE organization_id=%s AND project_id=%s",
                        (org, project),
                    )
                }
                if aliases.intersection(pages):
                    raise core.Rejected("A proposed article collides with a redirect.")
                for path in pages:
                    if heads.get(path) != body.expected_heads[path]:
                        raise core.Rejected(
                            "A newer guide version exists. Compare and review it first."
                        )
                title = event["title"]
                source = {
                    k: event[k]
                    for k in (
                        "id",
                        "source_url",
                        "revision",
                        "changed_paths",
                        "module_ids",
                    )
                    if k in event
                }
                source["title"] = title
            bundle = store.bundle(project, actor, body.item)
            result = {}
            for path, media in pages.items():
                markdown = bundle["files"][path]
                # An unchanged body and referenced bytes require no new revision.
                old = heads.get(path)
                if old:
                    current = edition(db, org, project, path, old)
                    if current["body"] == markdown and [
                        m["digest"] for m in current["media"]
                    ] == [m["digest"] for m in media]:
                        result[path] = old
                        continue
                digest = fingerprint([path, markdown, media, approval, old])
                from .onboarding import binding

                limit = int(
                    binding(org, project).get(
                        "guide_media_quota_bytes", 256 * 1024 * 1024
                    )
                )
                used = db.execute(
                    "SELECT coalesce(sum(octet_length(content)),0) FROM docs_guide_media WHERE organization_id=%s AND project_id=%s",
                    (org, project),
                ).fetchone()[0]
                for m in media:
                    raw = base64.b64decode(
                        bundle["evidence_files"][m["path"]], validate=True
                    )
                    if core.digest(raw) != m["digest"]:
                        raise core.Rejected("Media changed since approval.")
                    exists = db.execute(
                        "SELECT 1 FROM docs_guide_media WHERE organization_id=%s AND project_id=%s AND digest=%s",
                        (org, project, m["digest"]),
                    ).fetchone()
                    if not exists:
                        used += len(raw)
                        if used > limit:
                            raise core.Rejected(
                                "The workspace media quota would be exceeded."
                            )
                    db.execute(
                        "INSERT INTO docs_guide_media VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (
                            org,
                            project,
                            m["digest"],
                            mimetypes.guess_type(m["path"])[0],
                            raw,
                        ),
                    )
                db.execute(
                    """INSERT INTO docs_guide_versions(organization_id,project_id,path,digest,parent,item_id,approval,body,media,source,actor)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        org,
                        project,
                        path,
                        digest,
                        old,
                        body.item,
                        approval,
                        markdown,
                        Jsonb(media),
                        Jsonb(source),
                        actor,
                    ),
                )
                db.execute(
                    """INSERT INTO docs_guide_heads VALUES(%s,%s,%s,%s) ON CONFLICT (organization_id,project_id,path)
                     DO UPDATE SET digest=excluded.digest""",
                    (org, project, path, digest),
                )
                result[path] = digest
            db.execute(
                "INSERT INTO docs_library_saves VALUES(%s,%s,%s,%s,%s)",
                (org, project, body.item, approval, Jsonb(result)),
            )
            return dict(status="recorded", versions=result)

    @routes.get(base + "/version")
    def read(org: str, project: str, path: str, digest: str, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor)
            value = edition(db, org, project, path, digest)
            old = (
                edition(db, org, project, path, value["parent"])
                if value["parent"]
                else {"body": "", "media": []}
            )
            value["diff"] = "".join(
                difflib.unified_diff(
                    old["body"].splitlines(True),
                    value["body"].splitlines(True),
                    fromfile="previous/" + path,
                    tofile="reviewed/" + path,
                )
            )
            value["previous_media"] = old["media"]
            return value

    @routes.get(base + "/media/{media}")
    def get_media(
        org: str, project: str, media: str, path: str, version: str, actor=Depends(auth)
    ):
        with pool.connection() as db:
            scope(db, org, project, actor)
            value = edition(db, org, project, path, version)
            if not any(m["digest"] == media for m in value["media"]):
                raise HTTPException(404, "Media unavailable.")
            row = db.execute(
                "SELECT mime,content FROM docs_guide_media WHERE organization_id=%s AND project_id=%s AND digest=%s",
                (org, project, media),
            ).fetchone()
            if not row or core.digest(bytes(row[1])) != media:
                raise core.Rejected("Stored guide media failed verification.")
            return Response(bytes(row[1]), media_type=row[0])

    @routes.post(base + "/assets")
    def create_asset(org: str, project: str, body: AssetDraft, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor, True)
            value = edition(db, org, project, path_name(body.path), body.digest)
            head = db.execute(
                "SELECT digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s AND path=%s FOR UPDATE",
                (org, project, body.path),
            ).fetchone()
            if not head or head[0] != body.digest:
                raise core.Rejected("Select the current approved guide.")
            title = value["source"]["title"]
            # Keep the source guide's verified claims, checkpoints and linked evidence together.
            draft = (
                "# "
                + body.format
                + " · "
                + core.markdown_plain(title)
                + "\n\nAudience: "
                + core.markdown_plain(body.audience)
                + "\n\n"
                + value["body"]
            )
            ident = db.execute(
                """INSERT INTO docs_enablement(id,organization_id,project_id,path,digest,audience,format,body,owner_id)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(organization_id,project_id,path,digest,audience,format)
              DO UPDATE SET owner_id=docs_enablement.owner_id RETURNING id""",
                (
                    uuid4(),
                    org,
                    project,
                    body.path,
                    body.digest,
                    body.audience,
                    body.format,
                    draft,
                    actor,
                ),
            ).fetchone()[0]
            return {"id": ident}

    @routes.post(base + "/assets/{ident}")
    def asset_decision(
        org: str, project: str, ident: UUID, body: AssetDecision, actor=Depends(auth)
    ):
        with pool.connection() as db:
            scope(db, org, project, actor, True)
            row = db.execute(
                """SELECT a.version,a.status,a.owner_id,a.path,a.digest,a.body,h.digest FROM docs_enablement a
              JOIN docs_guide_heads h USING(organization_id,project_id,path) WHERE a.organization_id=%s AND a.project_id=%s AND a.id=%s FOR UPDATE""",
                (org, project, ident),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Asset unavailable.")
            version, status, owner, path, digest, draft, head = row
            if body.action == "refresh":
                if actor != owner or body.version != version or head == digest:
                    raise core.Rejected("Select a stale asset at its current revision.")
                old = edition(db, org, project, path, digest)
                new = edition(db, org, project, path, head)
                if draft.count(old["body"]) != 1:
                    raise core.Rejected(
                        "Editorial changes overlap the source guide. Review the new version and merge your wording."
                    )
                replacement = draft.replace(old["body"], new["body"], 1)
                ident2 = db.execute(
                    """INSERT INTO docs_enablement(id,organization_id,project_id,path,digest,audience,format,body,owner_id)
                    SELECT %s,organization_id,project_id,path,%s,audience,format,%s,owner_id FROM docs_enablement WHERE id=%s
                    ON CONFLICT(organization_id,project_id,path,digest,audience,format) DO UPDATE SET owner_id=docs_enablement.owner_id RETURNING id""",
                    (uuid4(), head, replacement, ident),
                ).fetchone()[0]
                return dict(id=ident2, status="draft")
            if actor != owner or body.version != version or head != digest:
                raise core.Rejected(
                    "Only the owner can act on a current asset revision."
                )
            if body.action == "export":
                if status != "approved":
                    raise core.Rejected("Approve the asset first.")
                from ..docs_loop import package_bundle

                source = edition(db, org, project, path, digest)
                media = {}
                for m in source["media"]:
                    raw = db.execute(
                        "SELECT content FROM docs_guide_media WHERE organization_id=%s AND project_id=%s AND digest=%s",
                        (org, project, m["digest"]),
                    ).fetchone()[0]
                    media[m["path"]] = base64.b64encode(bytes(raw)).decode()
                db.execute(
                    "UPDATE docs_enablement SET exported_at=now() WHERE id=%s", (ident,)
                )
                return Response(
                    package_bundle(
                        {
                            "files": {path: draft},
                            "evidence_files": media,
                            "source_version": digest,
                            "patch": "",
                        }
                    ),
                    media_type="application/zip",
                )
            if body.action == "save":
                if not body.body or not body.body.strip():
                    raise core.Rejected("Supply the asset text.")
                draft = body.body
            from ..editions import media_dependencies

            expected = {
                m["path"] for m in edition(db, org, project, path, digest)["media"]
            }
            actual = {ref[2] for ref in media_dependencies(path, draft)}
            if not actual or not actual <= expected:
                raise core.Rejected("Keep verified guide evidence in this asset.")
            new_status = "draft" if body.action == "save" else "approved"
            db.execute(
                "UPDATE docs_enablement SET body=%s,status=%s,version=version+1,exported_at=NULL WHERE id=%s",
                (draft, new_status, ident),
            )
            return dict(status=new_status, version=version + 1)

    return routes
