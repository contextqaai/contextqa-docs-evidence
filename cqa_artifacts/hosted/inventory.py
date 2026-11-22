"""Preview, resume and apply a documentation import in its workspace."""

import time
from collections import Counter
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb

from ..core import Rejected
from ..loop import fingerprint
from . import repository_docs as reader
from .github_intake import github_access
from .onboarding import PREFIX, binding, setup


def access(db, org, project, actor):
    row = db.execute(
        """SELECT role FROM docs_memberships m JOIN docs_projects p
        ON p.organization_id=m.organization_id WHERE m.organization_id=%s AND p.id=%s AND subject=%s""",
        (org, project, actor),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Workspace unavailable.")
    if row[0] not in ("admin", "editor"):
        raise HTTPException(403, "An editor or administrator can import documentation.")


def scope_for(db, org, project):
    config = setup(db, org, project)
    if not config["connected"]:
        raise HTTPException(
            409, "Connect the documentation repository in Workspace settings first."
        )
    return {k: config[k] for k in ("docs_repo", "branch", "docs_root", "revision")}


def latest(db, org, project):
    return db.execute(
        """SELECT id,scope,commit_sha,manifest,status,summary FROM docs_imports
        WHERE organization_id=%s AND project_id=%s ORDER BY created_at DESC,id DESC LIMIT 1""",
        (org, project),
    ).fetchone()


def report(db, row):
    if not row:
        return None
    job, scope, revision, manifest, status, summary = row
    files = db.execute(
        """SELECT path,kind,status,issue,data->>'title',data->>'reader_path' FROM docs_import_files
        WHERE job_id=%s ORDER BY path""",
        (job,),
    ).fetchall()
    titles = Counter(title.casefold() for _, _, _, _, title, _ in files if title)
    routes = Counter(route for _, _, _, _, _, route in files if route)
    collisions = [
        f"Shared reader path {route} ({n} pages). Check the site routing before publishing."
        for route, n in sorted(routes.items())
        if n > 1
    ]
    return {
        "id": str(job),
        "scope": scope,
        "commit": revision,
        "status": status,
        "summary": summary,
        "warnings": manifest["warnings"] + collisions,
        "files": [
            {
                "path": p,
                "kind": k,
                "status": s,
                "issue": i,
                "title": t,
                "duplicate_title": bool(t and titles[t.casefold()] > 1),
            }
            for p, k, s, i, t, _ in files
        ],
    }


def apply_files(db, org, project, actor, row):
    job, scope, commit, manifest, _, _ = row
    files = db.execute(
        """SELECT path,kind,sha,data FROM docs_import_files
        WHERE job_id=%s AND status='ready' ORDER BY path""",
        (job,),
    ).fetchall()
    nav, assets = {}, {}
    for path, kind, blob, data in files:
        if kind == "navigation":
            nav.update(data)
        elif kind == "image":
            assets[path] = blob
    state = db.execute(
        "SELECT state FROM docs_projects WHERE organization_id=%s AND id=%s FOR UPDATE",
        (org, project),
    ).fetchone()[0]
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    counts["skipped"] = db.execute(
        "SELECT count(*) FROM docs_import_files WHERE job_id=%s AND status='skipped'",
        (job,),
    ).fetchone()[0]
    for path, kind, blob, data in files:
        if kind != "page":
            continue
        repo_path = "/".join(filter(None, [scope["docs_root"], path]))
        ident = uuid5(
            NAMESPACE_URL, "/".join((org, project, scope["docs_repo"], repo_path))
        )
        source = {
            "repo": scope["docs_repo"],
            "repo_path": repo_path,
            "reader_path": data["reader_path"],
            "navigation": nav.get(path, []),
            "images": [{**i, "sha": assets.get(i["path"])} for i in data["images"]],
            "blob": blob,
            "title": data["title"],
        }
        previous = db.execute(
            """SELECT version,source,article_id,body FROM docs_import_versions WHERE
            organization_id=%s AND project_id=%s AND path=%s ORDER BY version DESC LIMIT 1""",
            (org, project, path),
        ).fetchone()
        baseline = state["articles"].get(path)
        observed = manifest["before"].get(path)
        if (baseline and baseline["digest"] != observed) or (observed and not baseline):
            raise HTTPException(
                409, "Article changed since preview. Preview the repository again."
            )
        if baseline and (
            previous
            and previous[2] != ident
            or baseline["body"] != data["body"]
            and (not previous or baseline["body"] != previous[3])
        ):
            counts["skipped"] += 1
            db.execute(
                "UPDATE docs_import_files SET status='skipped',issue='Existing baseline conflicts with this source.' WHERE job_id=%s AND path=%s",
                (job, path),
            )
            continue
        if (
            previous
            and previous[1] == source
            and baseline
            and baseline["body"] == data["body"]
        ):
            counts["unchanged"] += 1
            continue
        version = previous[0] + 1 if previous else 1
        db.execute(
            """INSERT INTO docs_import_versions
            (organization_id,project_id,path,version,job_id,article_id,source,body) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (org, project, path, version, job, ident, Jsonb(source), data["body"]),
        )
        state["articles"][path] = {
            "path": path,
            "title": data["title"],
            "body": data["body"],
            "digest": fingerprint(data["body"]),
            "updated_at": time.time(),
            "imported": dict(
                id=str(ident), version=version, commit=commit, job=str(job), **source
            ),
        }
        counts["updated" if baseline else "created"] += 1
    if counts["created"] or counts["updated"]:
        state["audit"].append(
            {
                "at": time.time(),
                "actor": actor,
                "action": "articles:import",
                "item": str(job),
            }
        )
        db.execute(
            "UPDATE docs_projects SET state=%s,updated_at=now() WHERE organization_id=%s AND id=%s",
            (Jsonb(state), org, project),
        )
    db.execute(
        "UPDATE docs_imports SET status='imported',summary=%s WHERE id=%s",
        (Jsonb(counts), job),
    )


def router(pool, auth):
    routes = APIRouter()
    actor_dependency = Depends(auth)
    base = PREFIX + "/inventory"

    @routes.get(base)
    def current(org: str, project: str, actor=actor_dependency):
        with pool.connection() as db:
            access(db, org, project, actor)
            return report(db, latest(db, org, project))

    @routes.post(base + "/preview")
    def preview(org: str, project: str, actor=actor_dependency):
        with pool.connection() as db:
            access(db, org, project, actor)
            scope = scope_for(db, org, project)
        commit, files, warnings = reader.inventory(
            github_access(binding(org, project)), scope
        )
        with pool.connection() as db:
            access(db, org, project, actor)
            if scope_for(db, org, project) != scope:
                raise HTTPException(409, "Repository scope changed. Preview again.")
            articles = db.execute(
                "SELECT state->'articles' FROM docs_projects WHERE organization_id=%s AND id=%s",
                (org, project),
            ).fetchone()[0]
            job = uuid4()
            db.execute(
                """INSERT INTO docs_imports(id,organization_id,project_id,scope,commit_sha,manifest)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (
                    job,
                    org,
                    project,
                    Jsonb(scope),
                    commit,
                    Jsonb(
                        {
                            "warnings": warnings,
                            "before": {p: v["digest"] for p, v in articles.items()},
                        }
                    ),
                ),
            )
            with db.cursor() as cur:
                cur.executemany(
                    "INSERT INTO docs_import_files(job_id,path,kind,sha,status,issue) VALUES(%s,%s,%s,%s,%s,%s)",
                    [
                        (job, p, k, h, "skipped" if i else "pending", i)
                        for p, (k, h, i) in files.items()
                    ],
                )
            return report(db, latest(db, org, project))

    @routes.post(base + "/{job}/{action}")
    def progress(
        org: str, project: str, job: UUID, action: str, actor=actor_dependency
    ):
        with pool.connection() as db:
            access(db, org, project, actor)
            scope = scope_for(db, org, project)
            row = latest(db, org, project)
            if not row or row[0] != job or row[1] != scope:
                raise HTTPException(
                    409,
                    "A newer preview or repository setting exists. Refresh the inventory.",
                )
            if action == "apply":
                if row[4] == "preview":
                    apply_files(db, org, project, actor, row)
                elif row[4] != "imported":
                    raise HTTPException(
                        409, "Finish reading the repository before importing."
                    )
            elif action == "read" and row[4] == "reading":
                file = db.execute(
                    "SELECT path,kind,sha FROM docs_import_files WHERE job_id=%s AND status='pending' ORDER BY path LIMIT 1",
                    (job,),
                ).fetchone()
                if file:
                    path, kind, blob = file
                    raw = reader.read_blob(
                        github_access(binding(org, project)),
                        scope["docs_repo"],
                        blob,
                        512_000 if kind == "image" else 100_000,
                    )
                    try:
                        data = reader.decode(path, kind, raw)
                    except (TypeError, ValueError, Rejected, RecursionError):
                        issue = {
                            "navigation": "Invalid or unsupported navigation configuration.",
                            "page": "Invalid or unsupported document. Check Markdown, front matter and MDX components.",
                            "image": "Invalid image.",
                        }[kind]
                        db.execute(
                            "UPDATE docs_import_files SET status='skipped',issue=%s WHERE job_id=%s AND path=%s",
                            (issue, job, path),
                        )
                    else:
                        db.execute(
                            "UPDATE docs_import_files SET status='ready',data=%s WHERE job_id=%s AND path=%s",
                            (Jsonb(data), job, path),
                        )
                if not db.execute(
                    "SELECT 1 FROM docs_import_files WHERE job_id=%s AND status='pending' LIMIT 1",
                    (job,),
                ).fetchone():
                    db.execute(
                        "UPDATE docs_imports SET status='preview' WHERE id=%s", (job,)
                    )
            elif action != "read":
                raise HTTPException(404, "Unknown import action.")
            return report(db, latest(db, org, project))

    @routes.get(base + "/figure/{job}")
    def figure(org: str, project: str, job: UUID, path: str, actor=actor_dependency):
        with pool.connection() as db:
            access(db, org, project, actor)
            result = db.execute(
                """SELECT f.data FROM docs_import_files f JOIN docs_imports j ON f.job_id=j.id
                WHERE j.organization_id=%s AND j.project_id=%s AND j.id=%s AND j.status='imported'
                AND f.kind='image' AND f.path=%s AND f.status='ready'""",
                (org, project, job, path),
            ).fetchone()
            if not result:
                raise HTTPException(404, "Figure unavailable.")
            return result[0]

    return routes
