"""Resolve each reader-visible media reference to a reviewed ContextQA step."""

import posixpath
import re
from pathlib import Path
from . import core, journeys
from .changes import reviewed
from .loop import fingerprint

MEDIA = re.compile(
    r"evidence/([a-f0-9]{64})/assets/([a-f0-9]{64})\.(png|jpg|webp|mp4|webm)$"
)
LINK = re.compile(r"!?\[(?:\\.|[^\]\\])*\]\(([^)\s]+)\)")


def media_dependencies(path, body):
    refs = []
    fence = ""
    visible_body = re.sub(r"<!--.*?(?:-->|$)", "", body, flags=re.DOTALL)
    for line in visible_body.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1].startswith(fence) and not marker[2].strip():
                fence = ""
            continue
        if marker:
            fence = marker[1]
            continue
        if line.startswith(("    ", "\t")):
            continue
        for link in LINK.finditer(line):
            target = posixpath.normpath(
                posixpath.join(posixpath.dirname(path), link[1])
            )
            match = MEDIA.fullmatch(target)
            if match:
                refs.append((match[1], match[2], target))
            elif "/assets/" in target and (
                "evidence/" in target or target.startswith("assets/")
            ):
                raise core.Rejected("Unresolved evidence link in " + path)
    return list(dict.fromkeys(refs))


def checked_media(item, event):
    """Validate only accepted articles and require per-page linked, traceable media."""
    available = {e["digest"]: e for e in item["evidence"]}
    verified = {}
    pages = {}
    for change in item["changes"]:
        if change["decision"] != "accepted":
            continue
        path = change["path"]
        deps = media_dependencies(path, change["after"])
        if not deps:
            raise core.Rejected(
                "Attach a reviewed ContextQA screenshot or video in "
                + path
                + " before delivery."
            )
        rows = []
        for digest, mid, target in deps:
            if digest not in available:
                raise core.Rejected(
                    "Attach the matching reviewed capture to this request."
                )
            if digest not in verified:
                root = Path(available[digest]["export_path"])
                try:
                    capture = reviewed(root)
                    receipt = journeys.checked(
                        core.load_json(root / "journey-review.json")
                    )
                except (OSError, ValueError, KeyError):
                    raise core.Rejected(
                        "The reviewed journey export is unavailable."
                    ) from None
                execution = capture.get("execution", {})
                deployment = receipt.get("deployment") or {}
                revision = event.get("revision") or receipt.get("head_sha")
                if (
                    receipt.get("evidence_policy") != "contextqa-only-v1"
                    or fingerprint(capture) != digest
                    or receipt.get("export_digest") != digest
                    or execution.get("transport") != "ContextQA API"
                    or execution.get("verdict") != "passed"
                    or receipt.get("source_sha256") != execution.get("source_sha256")
                    or not revision
                    or deployment.get("confirmed") is not True
                    or deployment.get("commit_sha") != revision
                    or capture.get("capture_context", {}).get("commit_sha") != revision
                    or capture.get("capture_context", {}).get("workflow_id") != receipt.get("journey_id")
                    or receipt.get("head_sha") != revision
                    or receipt.get("run_id") != execution.get("run_id")
                    or deployment.get("run_id") != execution.get("run_id")
                ):
                    raise core.Rejected(
                        "The attachment needs a passing, deployment-bound ContextQA review."
                    )
                verified[digest] = (capture, receipt)
            capture, receipt = verified[digest]
            origin = next(
                (
                    o
                    for o in receipt.get("media_origins", [])
                    if o.get("media_id") == mid and o.get("step_result_id")
                ),
                None,
            )
            medium = next(
                (
                    m
                    for m in capture["media"]
                    if m["id"] == mid
                    and target == "evidence/" + digest + "/" + m["path"]
                ),
                None,
            )
            if (
                not origin
                or not medium
                or not any(
                    mid in s["media"]
                    and s.get("step_result_id") == origin["step_result_id"]
                    for s in capture["steps"]
                )
            ):
                raise core.Rejected(
                    "Media must resolve to its reviewed ContextQA step."
                )
            rows.append(
                dict(
                    path=target,
                    kind=medium["kind"],
                    digest=mid,
                    export=digest,
                    journey=receipt["journey_id"],
                    run=receipt["run_id"],
                    step=origin["step_result_id"],
                    revision=receipt["head_sha"],
                )
            )
        pages[path] = rows
    if not pages:
        raise core.Rejected("Accept at least one article.")
    return pages


def verify_article_links(item):
    """A navigation change cannot depend on an omitted new article in this request."""
    from urllib.parse import urlsplit, unquote

    proposed = {c["path"]: c for c in item["changes"]}
    for c in proposed.values():
        if c["decision"] != "accepted":
            continue
        for link in LINK.finditer(c["after"]):
            u = urlsplit(link[1])
            if u.scheme or u.netloc or not u.path:
                continue
            path = posixpath.normpath(
                posixpath.join(posixpath.dirname(c["path"]), unquote(u.path))
            )
            other = proposed.get(path)
            if other and other["kind"] == "new" and other["decision"] != "accepted":
                raise core.Rejected(
                    c["path"]
                    + " links to a new article that has not been accepted: "
                    + path
                )
