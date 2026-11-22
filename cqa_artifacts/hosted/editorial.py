"""Scoped writing rounds over an imported baseline and reviewed ContextQA captures."""

from datetime import datetime, timezone
import base64
import difflib
import mimetypes
import posixpath
import re
from pathlib import Path
from typing import Literal
from uuid import UUID
from urllib.parse import unquote, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .. import core, guides, journeys
from ..changes import reviewed
from ..loop import fingerprint, path_name
from .captures import private_root
from .github_intake import BoundConnection
from .onboarding import PREFIX, binding, setup
from .store import PostgresStore
from .profiles import profile


class Brief(BaseModel):
    path: str = Field(max_length=250)
    template: Literal["Reference", "Concept", "Tutorial"] = "Reference"
    audience: str = Field(default="", max_length=300)
    goal: str = Field(default="", max_length=500)
    prerequisite: str = Field(default="", max_length=1000)
    fact: str = Field(default="", max_length=3000)
    recovery: str = Field(default="", max_length=1000)
    source: str = Field(default="", max_length=500)
    capture: UUID | None = None
    profile_revision: int | None = Field(default=None, ge=1)


class Submission(BaseModel):
    item_id: str
    version: int
    mode: Literal["save", "generate", "no_change"]
    brief: Brief


def capture_for(db, org, project, ident, event):
    row = db.execute(
        """SELECT registry,journey,provider_run,revision FROM docs_capture_jobs
        WHERE organization_id=%s AND project_id=%s AND id=%s AND status='reviewed'""",
        (org, project, ident),
    ).fetchone()
    if not row:
        raise core.Rejected("Choose a reviewed capture from this project.")
    registry, name, run, revision = row
    root = private_root() / str(ident) / "reviewed"
    try:
        evidence = reviewed(root)
        receipt = journeys.checked(core.load_json(root / "journey-review.json"))
    except (OSError, ValueError, KeyError):
        raise core.Rejected("The reviewed journey export is unavailable.") from None
    journey = journeys.select(registry, name)
    execution = evidence.get("execution", {})
    if (
        receipt.get("evidence_policy") != "contextqa-only-v1"
        or not journeys.deployment_check(
            receipt.get("deployment"), journey, run, revision
        )
        or receipt["export_digest"] != fingerprint(evidence)
        or receipt["source_sha256"] != execution.get("source_sha256")
        or execution.get("verdict") != "passed"
        or execution.get("transport") != "ContextQA API"
        or execution.get("run_id") != run
        or event.get("revision", revision) != revision
    ):
        raise core.Rejected(
            "The reviewed capture must match this source revision and deployment."
        )
    context = evidence.get("capture_context", {})
    if (
        receipt.get("head_sha") != revision
        or receipt.get("journey_id") != name
        or receipt.get("run_id") != run
        or context.get("workflow_id") != name
        or context.get("commit_sha") != revision
    ):
        raise core.Rejected("The reviewed journey does not match the capture job.")
    wanted = event.get("journey_requirements", [])
    if wanted and not any(
        r["journey_id"] == name
        and r["export_digest"] == receipt["export_digest"]
        and r["source_sha256"] == receipt["source_sha256"]
        for r in wanted
    ):
        raise core.Rejected("Select the journey requested for this source.")
    if event.get("requires_screenshots") and not any(
        m["kind"] == "screenshot" for m in evidence["media"]
    ):
        raise core.Rejected("This change requires a reviewed screenshot.")
    origins = {o.get("media_id") for o in receipt.get("media_origins", [])}
    if any(m["id"] not in origins for m in evidence["media"]):
        raise core.Rejected("Selected media lack a reviewed ContextQA origin.")
    return root, evidence, receipt


def compiled(brief, item, source, capture, writing_profile=None):
    b = brief
    refs = [
        dict(
            id="reference",
            kind="product-reference",
            url=b.source,
            observed_at=source["observed_at"],
            summary=b.fact,
        )
    ]
    section = dict(
        id="details",
        kind="concept",
        title="What to know" if b.template == "Concept" else "Reference details",
        paragraphs=[b.fact],
        source_ids=["reference"],
        figure_ids=[],
    )
    root = Path(".")
    if capture:
        root, evidence, receipt = capture
        refs.append(
            dict(
                id="execution",
                kind="contextqa-run",
                url=receipt["deployment"]["application_url"],
                journey_id=receipt["journey_id"],
                run_id=receipt["run_id"],
                verdict="passed",
                deployment_verified=True,
                observed_at=source["observed_at"],
                summary=evidence["title"],
            )
        )
        section.update(
            kind="procedure",
            title="Follow the steps",
            steps=[s["instruction"] for s in evidence["steps"]],
            expected=b.fact,
            source_ids=["reference", "execution"],
            requires_execution=True,
        )
        if b.template != "Tutorial":
            section.update(
                kind="concept",
                title="Reference details"
                if b.template == "Reference"
                else "What to know",
            )
            section.pop("steps")
            section.pop("expected")
    if writing_profile and b.template != "Tutorial":
        section["title"] = "Customer outcome" if writing_profile["voice"] == "Business outcome" else "Technical details"
    sections = [section]
    if b.recovery:
        sections.append(
            dict(
                id="recovery",
                kind="troubleshooting",
                title="If you need help",
                paragraphs=[b.recovery],
                source_ids=["reference"],
                figure_ids=[],
            )
        )
    spec = dict(
        schema="editorial-guide-v1",
        id="guide-" + item["id"],
        title=item["title"],
        audience=b.audience,
        goal=b.goal,
        summary=b.goal,
        prerequisites=[b.prerequisite],
        figures=[],
        sources=refs,
        sections=sections,
        related=[dict(title="Product reference", url=b.source)],
        review=dict(editorial=False, independent_task_completion=False),
    )
    result = guides.compile_guide(spec, root)
    byline = "For " + core.markdown_plain(b.audience) + "."
    if writing_profile:
        byline = core.markdown_plain(writing_profile["brand"]) + " · " + byline
    body = result["markdown"].replace(
        "> Editorial draft. See quality-report.json for evidence and review gaps.",
        byline,
        1,
    )
    if capture:
        media = {m["id"]: m for m in evidence["media"]}
        lines = body.splitlines()
        offset = 0
        start = lines.index("## " + section["title"])
        offset = lines.index(core.markdown_plain(b.fact), start) + 1
        for number, step in enumerate(evidence["steps"], 1):
            for mid in step["media"]:
                m = media[mid]
                href = posixpath.relpath(
                    "evidence/" + receipt["export_digest"] + "/" + m["path"],
                    posixpath.dirname(b.path) or ".",
                )
                label = core.markdown_plain(step["title"])
                anchor = f"{number}. " + core.markdown_plain(step["instruction"])
                if b.template == "Tutorial" and mid == step["media"][0]:
                    offset = lines.index(anchor, start) + 1
                lines.insert(
                    offset,
                    f"{'!' if m['kind'] == 'screenshot' else ''}[Step {number} · {label}]({href})",
                )
                offset += 1
        body = "\n".join(lines) + "\n"
    return body, result["report"]


def propose(item, articles, path, guide, reason):
    before = articles.get(path, {}).get("body", "")
    change = next((c for c in item["changes"] if c["path"] == path), None)
    if change and change["before"] != before:
        raise core.Rejected(
            "The imported baseline changed. Reconcile the existing proposal first."
        )
    previous = change["after"] if change else before
    start = "<!-- contextqa:editorial:" + item["id"] + " -->"
    end = "<!-- /contextqa:editorial:" + item["id"] + " -->"
    if before or (previous and not previous.startswith(start)):
        guide = guide.replace("# ", "## ", 1)
    block = start + "\n" + guide.rstrip() + "\n" + end
    if start in previous or end in previous:
        if (
            previous.count(start) != 1
            or previous.count(end) != 1
            or previous.index(start) > previous.index(end)
        ):
            raise core.Rejected("The managed guide section has conflicting markers.")
        after = (
            previous[: previous.index(start)]
            + block
            + previous[previous.index(end) + len(end) :]
        )
    else:
        after = previous + ("\n\n" if previous else "") + block + "\n"
    if after == previous:
        return False
    if not change:
        change = dict(
            id=str(max((int(c["id"]) for c in item["changes"]), default=0) + 1),
            path=path,
            before=before,
            base_digest=fingerprint(before),
            kind="update" if before else "new",
        )
        item["changes"].append(change)
    change.update(
        after=after,
        decision="pending",
        reason=reason,
        source=item["event_id"],
        diff="".join(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile="before/" + path,
                tofile="after/" + path,
            )
        ),
    )
    return True


def router(pool, auth):
    routes = APIRouter()

    @routes.get(PREFIX + "/writing/{item_id}/repository-media")
    def repository_media(org: str, project: str, item_id: str, change: str,
                         side: Literal["before", "after"], ref: str, actor=Depends(auth)):
        missing = HTTPException(404, "The linked repository media is unavailable.")
        if ":" in ref or ref.startswith("//"):
            raise missing
        link = urlsplit(ref)
        if link.scheme or link.netloc or not link.path or link.path.startswith("/") or "\\" in ref:
            raise missing
        with pool.connection() as db:
            row = db.execute(
                """SELECT p.state->'items'->%s, m.role FROM docs_projects p
                   JOIN docs_memberships m ON m.organization_id=p.organization_id
                   WHERE p.organization_id=%s AND p.id=%s AND m.subject=%s""",
                (item_id, org, project, actor)
            ).fetchone()
            if not row or not row[0] or row[1] not in ("admin", "editor", "contributor"):
                raise missing
            item, role = row
            if role == "contributor" and item.get("assignee") != actor:
                raise missing
            entry = next((c for c in item["changes"] if c["id"] == change), None)
            if not entry or not any(ref == match[1] for match in
                    re.finditer(r"!?\[[^\]\n]*\]\(([^)\s]+)\)", entry[side] or "")):
                raise missing
            path = posixpath.normpath(posixpath.join(posixpath.dirname(entry["path"]), unquote(link.path)))
            if path.startswith(("/", "../")) or path == ".." or "\\" in path:
                raise missing
            # Proposed files can be newer than the imported baseline. Only an
            # operator can bind their local bytes and digest to this exact request.
            pinned = (binding(org, project).get("review_media", {}).get(item_id, {}).get(path)
                      if side == "after" else None)
            if pinned:
                try:
                    raw = core.regular_file(Path(pinned["file"]))
                except OSError:
                    raise missing from None
                if core.digest(raw) != pinned["sha256"]:
                    raise core.Rejected("The repository media changed after capture.")
            else:
                source = db.execute(
                    """SELECT f.data->>'src' FROM docs_import_versions v
                       JOIN docs_import_files f ON f.job_id=v.job_id AND f.path=%s
                       WHERE v.organization_id=%s AND v.project_id=%s AND v.path=%s AND v.body=%s
                       AND f.kind='image' AND f.status='ready'
                       AND EXISTS (SELECT FROM jsonb_array_elements(v.source->'images') img
                                   WHERE img->>'path'=f.path AND img->>'sha'=f.sha)
                       ORDER BY v.version DESC LIMIT 1""",
                    (path, org, project, entry["path"], entry["before"]),
                ).fetchone()
                if not source or not source[0]:
                    raise missing
                raw = base64.b64decode(source[0].split(",", 1)[1], validate=True)
        kind = "video" if path.lower().endswith((".mp4", ".webm")) else "screenshot"
        ext = core.media_extension(raw, kind)
        media_types = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
                       ".mp4": "video/mp4", ".webm": "video/webm"}
        return Response(raw, media_type=media_types[ext],
                        headers={"Cache-Control": "private, no-store"})

    @routes.get(PREFIX + "/writing/{item_id}/figures/{export_digest}/{media_id}")
    def figure(
        org: str,
        project: str,
        item_id: str,
        export_digest: str,
        media_id: str,
        actor=Depends(auth),
    ):
        store = PostgresStore(pool, org)
        with store.transaction(project) as state:
            item = state["items"].get(item_id)
            if not item or (
                state["members"].get(actor) == "contributor"
                and item.get("assignee") != actor
            ):
                raise HTTPException(404, "Figure unavailable.")
            store.authorize(state, actor, ("admin", "editor", "contributor"), item)
            attachment = next(
                (e for e in item["evidence"] if e["digest"] == export_digest), None
            )
            if not attachment:
                raise HTTPException(404, "Figure unavailable.")
            root = Path(attachment["export_path"])
        try:
            capture = reviewed(root)
        except (OSError, ValueError, KeyError):
            raise core.Rejected("The reviewed figure is unavailable.") from None
        if fingerprint(capture) != export_digest:
            raise core.Rejected("The capture changed after review.")
        media = next((m for m in capture["media"] if m["id"] == media_id), None)
        if not media:
            raise HTTPException(404, "Figure unavailable.")
        raw = core.regular_file(core.asset_file(root, media["path"]))
        if core.digest(raw) != media_id:
            raise core.Rejected("The reviewed media changed.")
        return Response(raw, media_type=mimetypes.guess_type(media["path"])[0])

    @routes.post(PREFIX + "/writing")
    def write(org: str, project: str, body: Submission, actor=Depends(auth)):
        with pool.connection() as db:
            store = PostgresStore(BoundConnection(db), org)
            with store.transaction(project) as state:
                store.authorize(state, actor)
                item = store.get_item(state, body.item_id)
                b = body.brief
                fields = b.model_dump(mode="json", exclude_none=True)
                fields["capture"] = str(b.capture) if b.capture else None
                writing_profile = None
                if b.profile_revision is not None:
                    writing_profile = profile(db, org, project, b.profile_revision)
                    if writing_profile is None:
                        raise core.Rejected("Choose a writing profile revision from this workspace.")
                signature = fingerprint([actor, body.model_dump(mode="json")])
                old = item.get("writing", {})
                if (
                    old.get("request") == signature
                    and old["item_version"] == item["version"]
                ):
                    return {"status": old["status"], "version": item["version"]}
                store.editable(item, body.version)
                event = state["events"][item["event_id"]]["event"]
                if b.path:
                    path_name(b.path)
                missing = []
                for key, label in (
                    ("path", "article path"),
                    ("audience", "reader"),
                    ("goal", "reader goal"),
                    ("prerequisite", "prerequisite"),
                    ("fact", "supported fact or expected result"),
                    ("source", "source URL"),
                ):
                    if not fields[key].strip():
                        missing.append(label)
                if b.template == "Tutorial" and not b.capture:
                    missing.append("reviewed ContextQA capture")
                if b.source:
                    guides.url(b.source)
                    if re.search(r"[\s<>()\\]", b.source):
                        raise core.Rejected("Use an encoded HTTPS reference URL.")
                status = "in_progress"
                report = None
                if body.mode == "no_change":
                    if not b.fact.strip() or not b.source:
                        raise core.Rejected(
                            "Supply the no-change reason and its source."
                        )
                    if (
                        item["changes"]
                        or item["evidence"]
                        or event.get("requires_capture")
                        or event.get("requires_screenshots")
                        or event.get("journey_requirements")
                    ):
                        raise core.Rejected(
                            "Existing changes or evidence requirements need review."
                        )
                    if any(
                        not q.startswith(
                            ("No section matches.", "Supply supported replacement text")
                        )
                        for q in item["questions"]
                    ):
                        raise core.Rejected(
                            "Resolve the outstanding source questions first."
                        )
                    item["questions"] = []
                    item["status"] = status = "no_change"
                    missing = []
                elif body.mode == "generate":
                    if missing:
                        raise core.Rejected(
                            "Complete the writing brief: " + ", ".join(missing) + "."
                        )
                    cap = (
                        capture_for(db, org, project, b.capture, event)
                        if b.capture
                        else None
                    )
                    content, report = compiled(
                        b,
                        item,
                        {
                            "observed_at": datetime.fromtimestamp(
                                item["created_at"], timezone.utc
                            )
                            .date()
                            .isoformat()
                        },
                        cap,
                        writing_profile,
                    )
                    changed = propose(item, state["articles"], b.path, content, b.goal)
                    if (
                        not changed
                        and old.get("status") == "drafted"
                        and old.get("brief") == fields
                    ):
                        return {"status": "drafted", "version": item["version"]}
                    if cap and not any(
                        e["digest"] == cap[2]["export_digest"] for e in item["evidence"]
                    ):
                        root, evidence, receipt = cap
                        item["evidence"].append(
                            dict(
                                digest=receipt["export_digest"],
                                execution=evidence["execution"],
                                media_count=len(evidence["media"]),
                                title=evidence["title"],
                                export_path=str(root.resolve()),
                                capture_context=evidence["capture_context"],
                            )
                        )
                    item["questions"] = [
                        q
                        for q in item["questions"]
                        if q
                        != "Supply supported replacement text or explain no change for "
                        + b.path
                        and not q.startswith("No section matches.")
                    ]
                    if cap:
                        item["questions"] = [
                            q
                            for q in item["questions"]
                            if q
                            != "Attach a reviewed ContextQA export for the changed workflow before delivery."
                        ]
                    item["status"] = "needs_input" if item["questions"] else "open"
                    status = "drafted"
                elif old.get("brief") == fields and old.get("status") in (
                    "in_progress",
                    "drafted",
                ):
                    return {"status": old["status"], "version": item["version"]}
                if (
                    old.get("brief") == fields
                    and old.get("status") == status
                    and body.mode == "no_change"
                ):
                    return {"status": status, "version": item["version"]}
                item["approval"] = None
                if body.mode == "save":
                    item["status"] = "needs_input"
                item["version"] += 1
                if old and (
                    old.get("status") != "in_progress" or status != "in_progress"
                ):
                    item.setdefault("writing_history", []).append(
                        {
                            key: old.get(key)
                            for key in (
                                "brief",
                                "status",
                                "actor",
                                "item_version",
                                "source_digest",
                                "compiler",
                            )
                        }
                    )
                current = setup(db, org, project)
                destination = (
                    {k: current[k] for k in ("docs_repo", "branch", "docs_root")}
                    if current["connected"]
                    else None
                )
                item["writing"] = dict(
                    destination=destination,
                    brief=fields,
                    status=status,
                    missing=missing,
                    report=report,
                    request=signature,
                    item_version=item["version"],
                    source_digest=state["events"][item["event_id"]]["digest"],
                    compiler="editorial-guide-v1",
                    actor=actor,
                )
                store.log(state, actor, "writing:" + body.mode, item["id"])
                return {"status": status, "version": item["version"]}

    return routes
