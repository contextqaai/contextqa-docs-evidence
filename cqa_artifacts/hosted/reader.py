"""Version-aware reader redirects and human-reviewed guide retirement."""

import posixpath
from urllib.parse import unquote, urlsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..editions import LINK, checked_media
from .. import core
from ..loop import path_name
from .library import edition, scope
from .onboarding import PREFIX
from .store import PostgresStore
from .github_intake import BoundConnection


class Redirect(BaseModel):
    source: str
    target: str


class Retire(BaseModel):
    path: str
    version: str
    item: str
    reason: str = Field(min_length=4, max_length=2000)
    confirmed_task_removal: bool = False
    confirm_retirement: bool = False


def router(pool, auth):
    r = APIRouter()

    @r.post(PREFIX + "/reader/redirects")
    def redirect(org: str, project: str, body: Redirect, actor=Depends(auth)):
        src, target = path_name(body.source), path_name(body.target)
        with pool.connection() as db:
            scope(db, org, project, actor)
            store = PostgresStore(BoundConnection(db), org)
            with store.transaction(project):
                key = (org, project)
                heads = dict(
                    db.execute(
                        "SELECT path,digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s",
                        key,
                    )
                )
                if src in heads or src == target or target not in heads:
                    raise core.Rejected(
                        "Choose an unused source path and an existing guide as its destination."
                    )
                prior = db.execute(
                    "SELECT target FROM docs_reader_redirects WHERE organization_id=%s AND project_id=%s AND source=%s",
                    (*key, src),
                ).fetchone()
                if prior and prior[0] != target:
                    raise core.Rejected("This path already redirects to another guide.")
                db.execute(
                    "INSERT INTO docs_reader_redirects VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (*key, src, target, actor),
                )
                return dict(source=src, target=target)

    @r.get(PREFIX + "/reader/current")
    def current(org: str, project: str, path: str, actor=Depends(auth)):
        with pool.connection() as db:
            scope(db, org, project, actor)
            key = (org, project)
            row = db.execute(
                "SELECT target FROM docs_reader_redirects WHERE organization_id=%s AND project_id=%s AND source=%s",
                (*key, path),
            ).fetchone()
            target = row[0] if row else path
            head = db.execute(
                "SELECT digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s AND path=%s",
                (*key, target),
            ).fetchone()
            if not head:
                raise HTTPException(404, "Current guide unavailable.")
            return dict(
                path=target,
                digest=head[0],
                redirected=bool(row),
                **edition(db, org, project, target, head[0]),
            )

    @r.post(PREFIX + "/reader/retire")
    def retire(org: str, project: str, body: Retire, actor=Depends(auth)):
        key = (org, project)
        with pool.connection() as db:
            scope(db, org, project, actor)
            store = PostgresStore(BoundConnection(db), org)
            with store.transaction(project) as s:
                item = store.get_item(s, body.item)
                prior = db.execute(
                    "SELECT status FROM docs_guide_retirements WHERE organization_id=%s AND project_id=%s AND path=%s AND version=%s",
                    (*key, body.path, body.version),
                ).fetchone()
                if prior and prior[0] == "retired":
                    return {"status": "retired"}
                head = db.execute(
                    "SELECT digest FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s AND path=%s",
                    (*key, body.path),
                ).fetchone()
                if not head or head[0] != body.version:
                    raise core.Rejected("Review the current guide before retirement.")
                version = edition(db, org, project, body.path, body.version)
                event = s["events"][item["event_id"]]["event"]
                dependencies = []
                for p, content in db.execute(
                    """SELECT h.path,v.body FROM docs_guide_heads h JOIN docs_guide_versions v USING(organization_id,project_id,path,digest)
                    WHERE h.organization_id=%s AND h.project_id=%s AND h.path<>%s""",
                    (*key, body.path),
                ):
                    if any(
                        not urlsplit(link[1]).scheme
                        and posixpath.normpath(
                            posixpath.join(
                                posixpath.dirname(p), unquote(urlsplit(link[1]).path)
                            )
                        )
                        == body.path
                        for link in LINK.finditer(content)
                    ):
                        dependencies.append(p)
                dependencies.extend(
                    r[0]
                    for r in db.execute(
                        "SELECT source FROM docs_reader_redirects WHERE organization_id=%s AND project_id=%s AND target=%s",
                        (*key, body.path),
                    )
                )
                assets = [
                    str(r[0])
                    for r in db.execute(
                        "SELECT id FROM docs_enablement WHERE organization_id=%s AND project_id=%s AND path=%s AND digest=%s",
                        (*key, body.path, body.version),
                    )
                ]
                status = "investigate"
                if body.confirmed_task_removal:
                    if (
                        event.get("source") != "github"
                        or not event.get("revision")
                        or not item.get("approval")
                    ):
                        raise core.Rejected(
                            "Select an approved GitHub removal review with deployment-bound evidence."
                        )
                    if not db.execute(
                        "SELECT 1 FROM docs_source_deliveries WHERE organization_id=%s AND project_id=%s AND revision=%s",
                        (*key, event["revision"]),
                    ).fetchone():
                        raise core.Rejected(
                            "The removal revision needs a signed source receipt."
                        )
                    pages = checked_media(item, event)
                    if body.path not in pages:
                        raise core.Rejected(
                            "The evidence review must cover this guide."
                        )
                    status = "proposed"
                    if body.confirm_retirement:
                        if not prior or prior[0] != "proposed" or dependencies:
                            raise core.Rejected(
                                "Review the retirement proposal and resolve incoming links first."
                            )
                        db.execute(
                            "DELETE FROM docs_guide_heads WHERE organization_id=%s AND project_id=%s AND path=%s AND digest=%s",
                            (*key, body.path, body.version),
                        )
                        status = "retired"
                db.execute(
                    """INSERT INTO docs_guide_retirements(organization_id,project_id,path,version,item_id,reason,status,actor)
                     VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(organization_id,project_id,path,version)
                     DO UPDATE SET item_id=excluded.item_id,reason=excluded.reason,status=excluded.status,actor=excluded.actor""",
                    (
                        *key,
                        body.path,
                        body.version,
                        body.item,
                        body.reason,
                        status,
                        actor,
                    ),
                )
                return dict(
                    status=status,
                    incoming_links=dependencies,
                    derived_assets=assets,
                    media_count=len(version["media"]),
                )

    return r
