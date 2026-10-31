from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import stat
import urllib.error
import urllib.parse
import urllib.request
import zipfile

MAX_JSON = 4 * 1024 * 1024
MAX_TRACE = 64 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_MEDIA = 256 * 1024 * 1024
MAX_STEPS = 500
API = "https://server.contextqa.com"


class Rejected(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact(value: str) -> str:
    """Defense in depth for text; not a claim to detect every secret/PII."""
    value = re.sub(r"(?i)\b(?:token_[\w-]+\.[\w-]+|sk-[\w-]{12,}|Bearer\s+\S+)", "[REDACTED]", str(value))
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL REDACTED]", value)
    value = re.sub(r"https?://[^\s<>]+", "[URL OMITTED]", value)
    value = re.sub(r"(?i)\b(password|api[_ -]?key|authorization|cookie|secret)\s*[:=]\s*\S+", r"\1=[REDACTED]", value)
    return value[:4000]


def private_dir(path: Path) -> Path:
    if path.is_symlink():
        raise Rejected("Symlink directories are not supported")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def write_json(path: Path, value) -> None:
    if path.is_symlink():
        raise Rejected("Refusing symlink output")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


def load_json(path: Path):
    if path.is_symlink() or path.stat().st_size > MAX_JSON:
        raise Rejected("JSON input is a symlink or exceeds size limit")
    return json.loads(path.read_text())


def regular_file(path: Path, limit=MAX_MEDIA) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise Rejected("Expected a regular file within the size limit")
    return path.read_bytes()


def asset_file(root: Path, relative: str) -> Path:
    candidate = root / relative
    if (root / "assets").is_symlink() or not candidate.resolve().is_relative_to(root.resolve()):
        raise Rejected("Asset escapes workspace")
    return candidate


def init(root: Path, title: str) -> dict:
    private_dir(root)
    if (root / "manifest.json").exists():
        raise Rejected("Workspace already exists")
    private_dir(root / "assets")
    private_dir(root / "private")
    manifest = {"schema": 1, "title": redact(title), "source": "user-authored", "steps": [], "media": []}
    write_json(root / "manifest.json", manifest)
    return manifest


def manifest(root: Path) -> dict:
    data = load_json(root / "manifest.json")
    if data.get("schema") != 1 or not isinstance(data.get("steps"), list) or not isinstance(data.get("media"), list):
        raise Rejected("Unsupported manifest")
    if len(data["steps"]) > MAX_STEPS or len(data["media"]) > 500:
        raise Rejected("Workspace exceeds review limits")
    return data


def save(root: Path, data: dict) -> None:
    write_json(root / "manifest.json", data)


def add_step(root: Path, title: str, instruction: str) -> None:
    data = manifest(root)
    if len(data["steps"]) >= MAX_STEPS:
        raise Rejected("Too many steps")
    data["steps"].append({"title": redact(title), "instruction": redact(instruction), "media": [], "needs_review": False})
    save(root, data)


def edit_step(root: Path, number: int, title: str, instruction: str) -> None:
    data = manifest(root)
    if not 1 <= number <= len(data["steps"]):
        raise Rejected("Step not found")
    data["steps"][number - 1].update(title=redact(title), instruction=redact(instruction), needs_review=False)
    save(root, data)


def media_extension(data: bytes, kind: str) -> str:
    if kind == "screenshot":
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return ".webp"
    elif kind == "video":
        if data.startswith(b"\x1aE\xdf\xa3"):
            return ".webm"
        if len(data) > 12 and data[4:8] == b"ftyp":
            return ".mp4"
    raise Rejected("Only PNG/JPEG/WebP images or MP4/WebM video are accepted; HTML/SVG are not media")


def add_media_bytes(root: Path, payload: bytes, kind: str) -> str:
    if len(payload) > MAX_MEDIA:
        raise Rejected("Media exceeds size limit")
    ext = media_extension(payload, kind)
    sha = digest(payload)
    data = manifest(root)
    if any(m["id"] == sha for m in data["media"]):
        return sha
    if len(data["media"]) >= 500:
        raise Rejected("Too many media files")
    path = asset_file(root, "assets/" + sha + ext)
    if path.is_symlink():
        raise Rejected("Refusing symlink asset")
    path.write_bytes(payload)
    os.chmod(path, 0o600)
    data["media"].append({"id": sha, "kind": kind, "path": "assets/" + path.name, "sha256": sha})
    save(root, data)
    return sha


def add_media(root: Path, path: Path, kind: str) -> str:
    return add_media_bytes(root, regular_file(path), kind)


def attach(root: Path, number: int, media_id: str) -> None:
    data = manifest(root)
    if not 1 <= number <= len(data["steps"]) or media_id not in {m["id"] for m in data["media"]}:
        raise Rejected("Unknown step or media")
    step = data["steps"][number - 1]
    if media_id not in step["media"]:
        step["media"].append(media_id)
    save(root, data)


def capture_context(value: dict) -> dict:
    """Operator-supplied labels, never a substitute for execution evidence."""
    from datetime import datetime
    allowed = {"workflow_id", "app_version", "captured_at", "environment", "capture_method", "runner_mode", "commit_sha", "source_pr"}
    if not isinstance(value, dict) or not value or set(value) - allowed:
        raise Rejected("Capture context contains unsupported fields")
    for key, item in value.items():
        if not isinstance(item, str) or not item.strip() or len(item) > 200:
            raise Rejected("Capture context values must be short nonempty strings")
        if key == "captured_at":
            try:
                stamp = datetime.fromisoformat(item.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    raise ValueError()
            except ValueError:
                raise Rejected("Capture time must be an ISO timestamp with timezone") from None
        if key == "commit_sha" and not re.fullmatch(r"[a-f0-9]{40}", item):
            raise Rejected("Commit must be a full Git SHA")
    return {key: redact(item) for key, item in value.items()}


def set_context(root: Path, value: dict) -> None:
    checked = capture_context(value)
    data = manifest(root)
    data["capture_context"] = checked
    save(root, data)


def checked_annotations(items, step, media):
    if not isinstance(items, list) or len(items) > 20:
        raise Rejected("Select at most 20 annotations per step")
    result = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"media_id", "x", "y", "width", "height", "label"}:
            raise Rejected("Annotation requires media_id, x, y, width, height and label")
        mid = item["media_id"]
        if not isinstance(mid, str) or mid not in step["media"] or media.get(mid, {}).get("kind") != "screenshot":
            raise Rejected("Annotate only screenshots attached to this step")
        import math
        if any(type(item[k]) not in (int, float) or not math.isfinite(item[k]) or not 0 <= item[k] <= 100 for k in ("x", "y", "width", "height")):
            raise Rejected("Annotation coordinates must be finite percentages")
        if item["width"] <= 0 or item["height"] <= 0 or item["x"] + item["width"] > 100 or item["y"] + item["height"] > 100:
            raise Rejected("Annotation rectangle must fit the screenshot")
        if not isinstance(item["label"], str) or not item["label"].strip() or len(item["label"]) > 120:
            raise Rejected("Annotation needs a short label")
        result.append(dict(item, label=redact(item["label"])))
    return result


def annotate(root: Path, number: int, items: list) -> None:
    data = manifest(root)
    if not 1 <= number <= len(data["steps"]):
        raise Rejected("Step not found")
    step = data["steps"][number - 1]
    step["annotations"] = checked_annotations(items, step, {m["id"]: m for m in data["media"]})
    save(root, data)


def import_trace(root: Path, source: Path) -> dict:
    """Read a bounded Playwright archive; never extract DOM, sources or network bodies."""
    archive = regular_file(source, MAX_TRACE)
    count = frames = 0
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        infos = z.infolist()
        if len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_EXPANDED:
            raise Rejected("Trace archive exceeds limits")
        for i in infos:
            parts = Path(i.filename).parts
            if i.filename.startswith(("/", "\\")) or ".." in parts or "\\" in i.filename or stat.S_ISLNK(i.external_attr >> 16):
                raise Rejected("Unsafe archive path or symlink")
            if i.file_size > MAX_EXPANDED or i.file_size / max(i.compress_size, 1) > 200:
                raise Rejected("Suspicious archive expansion")
        # Parse all event streams before mutating the workspace.
        events = []
        for info in infos:
            if info.filename.endswith(".trace"):
                if info.file_size > 16 * 1024 * 1024:
                    raise Rejected("Trace event stream exceeds limit")
                for line in z.read(info).splitlines():
                    if len(line) > 1024 * 1024:
                        raise Rejected("Trace event exceeds limit")
                    if line.strip():
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            raise Rejected("Invalid trace event")
                        events.append(event)
                        if len(events) > 20000:
                            raise Rejected("Trace event count exceeds limit")
        names = {i.filename for i in infos}
        frame_members = []
        for event in events:
            if event.get("type") != "screencast-frame":
                continue
            if "file" in event:
                # Newer traces name an exact, flat screencast ZIP member.
                # Do not allow arbitrary archive paths, even when they exist.
                member = event["file"]
                if not isinstance(member, str) or not re.fullmatch(r"screencast/[A-Za-z0-9_@.-]{1,200}\.(?:jpeg|jpg|png|webp)", member):
                    raise Rejected("Invalid screencast frame reference")
            else:
                name = event.get("sha1", "")
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", name):
                    continue
                member = "resources/" + name
            if member in names:
                frame_members.append(member)
        safe_actions = {"click": "Click a control", "fill": "Fill a field", "goto": "Navigate to a page", "press": "Press a key", "check": "Select a checkbox", "selectOption": "Select an option"}
        data = manifest(root)
        for event in events:
            if event.get("type") == "before":
                action = str(event.get("method") or event.get("apiName", "").split(".")[-1])
                if action in safe_actions:
                    if len(data["steps"]) >= MAX_STEPS:
                        raise Rejected("Too many trace actions")
                    data["steps"].append({"title": safe_actions[action], "instruction": "", "media": [], "needs_review": True})
                    count += 1
        data["source"] = "playwright-trace"
        save(root, data)
        for member in frame_members:
            add_media_bytes(root, z.read(member), "screenshot")
            frames += 1
        if (root / "private").is_symlink():
            raise Rejected("Private directory must not be a symlink")
        trace_path = root / "private" / "source-trace.zip"
        if trace_path.is_symlink():
            raise Rejected("Refusing symlink trace destination")
        trace_path.write_bytes(archive)
        os.chmod(trace_path, 0o600)
    return {"captured_actions": count, "frame_events": frames, "video_created": False, "dom_exported": False, "requires_review": True}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Rejected("API redirect refused")


def api_read(token: str, endpoint: str) -> dict:
    if not re.fullmatch(r"/test_plan_results/[0-9]+/results|/test_case_results/[0-9]+|/test_step_results/[0-9]+", endpoint):
        raise Rejected("Only explicit existing-result GET endpoints are supported")
    request = urllib.request.Request(API + endpoint, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            raw = response.read(MAX_JSON + 1)
            if len(raw) > MAX_JSON:
                raise Rejected("API response exceeds limit")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise Rejected("Unexpected API response")
            return result
    except urllib.error.HTTPError as error:
        raise Rejected(f"ContextQA read refused (HTTP {error.code}); check scoped read permissions") from None
    except (urllib.error.URLError, TimeoutError):
        raise Rejected("ContextQA read failed; no request retry was attempted") from None


def collect(root: Path, token: str, run_id: int, case_ids: list[int], step_ids: list[int]) -> dict:
    if any(not isinstance(i, int) or i < 1 for i in [run_id, *case_ids, *step_ids]):
        raise Rejected("Result IDs must be positive integers")
    summary = api_read(token, f"/test_plan_results/{run_id}/results")
    cases = [api_read(token, f"/test_case_results/{i}") for i in case_ids]
    for case in cases:
        if str(case.get("testPlanResultId")) != str(run_id):
            raise Rejected("Case result does not attest membership in the requested run")
    steps = [api_read(token, f"/test_step_results/{i}") for i in step_ids]
    for step in steps:
        if str(step.get("testCaseResultId")) not in {str(i) for i in case_ids}:
            raise Rejected("Step result does not belong to an explicitly selected case result")
    # Raw results and remote media references are private; URLs may be signed credentials.
    if (root / "private").is_symlink():
        raise Rejected("Private directory must not be a symlink")
    write_json(root / "private" / "contextqa-results.json", {"summary": summary, "cases": cases, "steps": steps})
    kinds = {"screenRecordingUrl": "video", "screenRecordings": "video", "screenShotURL": "screenshot", "screenshotUrl": "screenshot", "snapshotUrl": "snapshot-reference", "traceViewerUrl": "trace-viewer", "traceViewers": "trace-viewer", "reportFileUrl": "report", "logUrl": "logs"}
    references = []
    for record in [summary, *cases, *steps]:
        for field, kind in kinds.items():
            values = record.get(field)
            if isinstance(values, str):
                values = [values]
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str) and value.startswith("https://"):
                        references.append({"kind": kind, "url": value})
    write_json(root / "private" / "artifact-references.json", references)
    result = {k: summary.get(k) for k in ["status", "result", "totalCount", "passedCount", "failedCount"]}
    result.update(case_results_read=len(cases), step_results_read=len(steps), artifact_references=len(references), media_downloaded=False, paid_execution_started=False)
    return result


def clean_export(root: Path) -> dict:
    data = manifest(root)
    used = {mid for step in data["steps"] for mid in step.get("media", [])}
    media = []
    for item in data["media"]:
        if item.get("id") not in used:
            continue
        relative = item.get("path", "")
        if not re.fullmatch(r"assets/[a-f0-9]{64}\.(png|jpg|webp|mp4|webm)", relative):
            raise Rejected("Invalid media path")
        raw = regular_file(asset_file(root, relative))
        if digest(raw) != item.get("sha256") or item.get("id") != item.get("sha256"):
            raise Rejected("Media digest mismatch")
        extension = media_extension(raw, item.get("kind"))
        if not relative.endswith(extension):
            raise Rejected("Media content/type mismatch")
        media.append({k: item[k] for k in ["id", "kind", "path", "sha256"]})
    known = {m["id"] for m in media}
    steps = []
    for step in data["steps"]:
        if step.get("needs_review") or not step.get("instruction", "").strip():
            raise Rejected("Every imported action needs audience-specific reviewed instructions")
        if any(i not in known for i in step.get("media", [])):
            raise Rejected("Unknown attached media")
        cleaned = {"title": redact(step["title"]), "instruction": redact(step["instruction"]), "media": step.get("media", [])}
        if "annotations" in step:
            cleaned["annotations"] = checked_annotations(step["annotations"], step, {m["id"]: m for m in media})
        for field in ("case_result_id", "step_result_id"):
            if field in step:
                if type(step[field]) is not int or step[field] < 1:
                    raise Rejected("Invalid ContextQA result reference")
                cleaned[field] = step[field]
        steps.append(cleaned)
    if not steps:
        raise Rejected("Add at least one reviewed step")
    result = {"schema": 1, "title": redact(data["title"]), "steps": steps, "media": media}
    if "capture_context" in data:
        result["capture_context"] = capture_context(data["capture_context"])
    if "execution" in data:
        execution = data["execution"]
        required = {"run_id", "transport", "collected_at", "status", "result", "verdict", "case_result_ids", "step_result_ids", "source_sha256", "media_downloaded"}
        if not isinstance(execution, dict) or set(execution) != required:
            raise Rejected("Invalid ContextQA execution provenance")
        if type(execution["run_id"]) is not int or execution["run_id"] < 1 or execution["transport"] not in ("ContextQA API", "simulated"):
            raise Rejected("Invalid ContextQA execution provenance")
        if execution["verdict"] not in ("passed", "failed", "inconclusive") or not re.fullmatch(r"[a-f0-9]{64}", str(execution["source_sha256"])):
            raise Rejected("Invalid ContextQA execution provenance")
        if not isinstance(execution["collected_at"], str) or any(execution[field] is not None and not isinstance(execution[field], str) for field in ("status", "result")) or execution["media_downloaded"] is not False:
            raise Rejected("Invalid ContextQA execution provenance types")
        for field in ("case_result_ids", "step_result_ids"):
            if not isinstance(execution[field], list) or len(execution[field]) > 100 or any(type(i) is not int or i < 1 for i in execution[field]):
                raise Rejected("Invalid ContextQA result references")
        result["execution"] = {key: redact(value) if isinstance(value, str) else value for key, value in execution.items()}
    return result


def export_digest(data: dict) -> str:
    return digest(json.dumps(data, sort_keys=True, ensure_ascii=False).encode())


def approve(root: Path, reviewer: str, confirmed: bool) -> str:
    if not confirmed or not reviewer.strip():
        raise Rejected("Explicit rights, content and media review confirmation is required")
    sha = export_digest(clean_export(root))
    write_json(root / "approval.json", {"digest": sha, "reviewer": redact(reviewer), "rights_and_media_review_confirmed": True})
    return sha


def _render(data: dict) -> str:
    e = html.escape
    media = {m["id"]: m for m in data["media"]}
    sections = []
    for number, step in enumerate(data["steps"], 1):
        content = []
        for key in step["media"]:
            m = media[key]
            src = e(m["path"], quote=True)
            if m["kind"] == "screenshot":
                boxes = []
                labels = []
                for annotation in step.get("annotations", []):
                    if annotation["media_id"] != key:
                        continue
                    label = e(annotation["label"])
                    boxes.append(f'<span class="annotation" style="left:{annotation["x"]}%;top:{annotation["y"]}%;width:{annotation["width"]}%;height:{annotation["height"]}%" aria-label="{label}"><b>{len(labels)+1}</b></span>')
                    labels.append(f'<li>{label}</li>')
                content.append(f'<figure><div class="frame"><img src="{src}" alt="Reviewed screenshot for step {number}" loading="lazy">{"".join(boxes)}</div>' + ('<figcaption><ol>' + ''.join(labels) + '</ol></figcaption>' if labels else '') + '</figure>')
            else:
                content.append(f'<video controls preload="metadata" src="{src}"></video>')
        sections.append(f'<section id="step-{number}"><h2>{number}. {e(step["title"])}</h2><p>{e(step["instruction"])}</p>{"".join(content)}<nav>' + (f'<a href="#step-{number-1}">Previous</a> ' if number > 1 else '') + (f'<a href="#step-{number+1}">Next</a>' if number < len(data["steps"]) else '<a href="#top">Start again</a>') + '</nav></section>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; img-src &#39;self&#39;; media-src &#39;self&#39;; style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;; frame-src &#39;none&#39;"><title>' + e(data["title"]) + '</title><style>body{font:18px/1.6 system-ui;max-width:960px;margin:40px auto;padding:20px;color:#162035}section{padding:24px 0;border-bottom:1px solid #ddd}img,video{max-width:100%;height:auto}a{color:#1559a8;margin-right:24px}nav{margin:20px 0}</style><main id="top"><h1>' + e(data["title"]) + '</h1><p>Reviewed static walkthrough. This does not control a live customer browser.</p>' + ''.join(sections) + '</main></html>'


def execution_note(data: dict) -> str:
    info = data.get("execution")
    if not info:
        return ""
    label = "SIMULATED TRANSPORT — no live ContextQA execution" if info["transport"] == "simulated" else "ContextQA API result snapshot"
    return f'{label}; run {info["run_id"]}; status {info["status"]}; result {info["result"]}; assessment {info["verdict"]}; collected {info["collected_at"]}. Media is included only when separately obtained, reviewed and attached.'


def write_brand(target: Path) -> None:
    source = Path(__file__).parent / "brand/contextqa-logo.svg"
    shutil.copyfile(source, target / "assets/contextqa-logo.svg")
    os.chmod(target / "assets/contextqa-logo.svg", 0o600)


def render(data: dict) -> str:
    page = _render(data)
    page = page.replace('<main id="top">', '<main id="top"><div style="background:#101828;padding:16px 24px;border-radius:12px"><img src="assets/contextqa-logo.svg" alt="ContextQA" style="width:180px;max-height:56px"></div>', 1)
    page = page.replace('</style>', 'figure{margin:20px 0}.frame{position:relative;display:inline-block;line-height:0;max-width:100%}.frame img{display:block}.annotation{position:absolute;box-sizing:border-box;border:3px solid #b31b41;pointer-events:none}.annotation b{position:absolute;left:0;top:0;background:#b31b41;color:white;font:700 14px/1.5 system-ui;padding:0 5px}.capture-context{padding:16px;background:#f2f5fa;font-size:14px}</style>')
    context = data.get("capture_context")
    if context:
        labels = '; '.join(k.replace('_', ' ') + ': ' + v for k, v in context.items())
        page = page.replace('<main id="top">', '<main id="top"><p class="capture-context">Capture labels (operator supplied): ' + html.escape(labels) + '</p>', 1)
    note = execution_note(data)
    return page.replace('<main id="top">', '<main id="top"><p>' + html.escape(note) + '</p>', 1) if note else page


def markdown_plain(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>-])", r"\\\1", html.escape(value))


def export(root: Path, target: Path, base_url: str) -> dict:
    data = clean_export(root)
    approval = load_json(root / "approval.json")
    if not approval.get("rights_and_media_review_confirmed") or approval.get("digest") != export_digest(data):
        raise Rejected("Approval missing or invalidated by changes; review again")
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise Rejected("Embed base must be a credential-free HTTPS URL with no query or fragment")
    if target.exists() or target.is_symlink():
        raise Rejected("Export target must not exist; refusing overwrite or mixed private data")
    # Public output is newly created, never copied from the private workspace wholesale.
    private_dir(target)
    private_dir(target / "assets")
    for item in data["media"]:
        destination = target / item["path"]
        shutil.copyfile(asset_file(root, item["path"]), destination)
        os.chmod(destination, 0o600)
    write_brand(target)
    write_json(target / "manifest.json", data)
    write_json(target / "review-receipt.json", {"digest": export_digest(data), "rights_and_media_review_confirmed": True})
    (target / "index.html").write_text(render(data))
    lines = ["# " + markdown_plain(data["title"]), "", "Reviewed workflow evidence; verify the target product version before publishing.", ""]
    if data.get("execution"):
        lines += [markdown_plain(execution_note(data)), ""]
    if data.get("capture_context"):
        lines += ["Capture labels (operator supplied):", ""]
        lines += [f'- {markdown_plain(k.replace("_", " "))}: {markdown_plain(v)}' for k, v in data["capture_context"].items()]
        lines += [""]
    for n, step in enumerate(data["steps"], 1):
        lines += [f'## {n}. {markdown_plain(step["title"])}', "", markdown_plain(step["instruction"]), ""]
        for mid in step["media"]:
            m = next(m for m in data["media"] if m["id"] == mid)
            prefix = "!" if m["kind"] == "screenshot" else ""
            lines += [f'{prefix}[{m["kind"]} for step {n}]({m["path"]})', ""]
        if step.get("annotations"):
            lines += [f'[View annotated screenshots](index.html#step-{n})', ""]
            lines += [f'- {markdown_plain(a["label"])}' for a in step["annotations"]]
            lines += [""]
    (target / "guide.md").write_text("\n".join(lines))
    src = html.escape(base_url.rstrip('/') + '/index.html', quote=True)
    (target / "embed.html.txt").write_text(f'<iframe src="{src}" title="{html.escape(data["title"], quote=True)}" sandbox="" referrerpolicy="no-referrer" loading="lazy" width="100%" height="720"></iframe>\n')
    write_json(target / "handoff.json", {"format": "contextqa-reviewed-evidence-v1", "layerpath": {"mode": "manual_media_import", "instructions": "Upload approved images or video and use the reviewed steps as the project brief. No Layerpath API is assumed."}, "ekline": {"mode": "documentation_draft", "instructions": "Use guide.md and manifest.json as evidence for a reviewed documentation draft. No EkLine API is assumed."}})
    for item in target.iterdir():
        if item.is_file():
            os.chmod(item, 0o600)
    return {"exported": True, "steps": len(data["steps"]), "media": len(data["media"]), "raw_trace_exported": False, "original_dom_exported": False, "remote_media_fetched": False}
