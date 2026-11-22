"""Read a bounded, immutable Git tree and interpret static documentation as data."""

import base64
import hashlib
import json
import posixpath
import re
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from fastapi import HTTPException

from ..loop import path_name, text
from .github_intake import github_get

RASTER = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
CONFIG = {"docs.json", "mint.json"}
UNSUPPORTED = {
    "mkdocs.yml",
    "mkdocs.yaml",
    "docusaurus.config.js",
    "docusaurus.config.ts",
    "sidebars.js",
    "sidebars.ts",
}


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{40}", value):
        raise HTTPException(502, "GitHub returned an invalid object identifier.")
    return value


def inventory(config, scope):
    repo = "/repos/" + scope["docs_repo"]
    head = github_get(config, repo + "/commits/" + quote(scope["branch"], safe=""))
    revision = sha(head["sha"])
    root_tree = sha(head["commit"]["tree"]["sha"])

    def tree(ident, recursive=False):
        result = github_get(
            config,
            repo + "/git/trees/" + ident,
            {"recursive": "1"} if recursive else None,
        )
        if result.get("truncated") is not False or not isinstance(
            result.get("tree"), list
        ):
            raise HTTPException(
                409,
                "Repository listing is incomplete. Existing articles are safe. Retry the preview or choose a smaller docs directory.",
            )
        return result["tree"]

    for part in filter(None, scope["docs_root"].split("/")):
        child = next(
            (x for x in tree(root_tree) if x["type"] == "tree" and x["path"] == part),
            None,
        )
        if not child:
            raise HTTPException(
                409, "The selected docs directory is missing on this branch."
            )
        root_tree = sha(child["sha"])
    files, warnings, total = {}, [], 0
    for entry in tree(root_tree, True):
        path = entry["path"]
        parts = PurePosixPath(path).parts
        if (
            not parts
            or path.startswith("/")
            or ".." in parts
            or any(p.startswith(".") for p in parts)
        ):
            continue
        if entry.get("mode") not in ("100644", "100755") or entry["type"] != "blob":
            continue
        suffix = PurePosixPath(path).suffix.lower()
        if path in CONFIG:
            kind = "navigation"
        elif path in UNSUPPORTED:
            warnings.append(
                f"{path}: navigation format unsupported. Repository paths remain available."
            )
            continue
        elif suffix in RASTER:
            kind = "image"
        elif suffix in (".md", ".mdx"):
            kind = "page"
        else:
            continue
        size = entry.get("size")
        if type(size) is not int or size < 0:
            raise HTTPException(502, "GitHub omitted a file size. Retry the preview.")
        issue = None
        if size > (512_000 if kind == "image" else 100_000):
            issue = "File exceeds the supported preview size."
        else:
            total += size
        files[path] = (kind, sha(entry["sha"]), issue)
    if len(files) > 500 or total > 12_000_000:
        raise HTTPException(
            422,
            "Choose a smaller docs directory (up to 500 supported files and 12 MB).",
        )
    return revision, files, warnings


def read_blob(config, repo, blob, limit):
    data = github_get(config, "/repos/" + repo + "/git/blobs/" + sha(blob))
    if data.get("encoding") != "base64":
        raise HTTPException(502, "GitHub returned an incomplete blob. Retry the read.")
    try:
        raw = base64.b64decode("".join(data["content"].split()), validate=True)
    except (KeyError, AttributeError, ValueError):
        raise HTTPException(
            502, "GitHub returned unreadable blob data. Resume the preview."
        ) from None
    if (
        len(raw) > limit
        or hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        != blob
    ):
        raise HTTPException(
            502, "The downloaded file did not match the listed blob. Retry the read."
        )
    return raw


def navigation(raw):
    data = json.loads(raw)
    nav = data.get("navigation") if isinstance(data, dict) else None
    if not isinstance(nav, (list, dict)):
        raise TypeError("Expected a navigation object or list.")

    def field(value):
        if "\0" in value:
            raise ValueError("Invalid navigation text.")
        value.encode("utf-8")
        return value

    mapping = {}

    def visit(node, trail):
        if isinstance(node, str):
            if node.startswith(("https:", "http:", "#")):
                return
            route = field(node).strip("/")
            for ext in (".md", ".mdx"):
                mapping[route.removesuffix(ext) + ext] = trail
        elif isinstance(node, list):
            for child in node:
                visit(child, trail)
        elif isinstance(node, dict):
            label = next(
                (
                    node[k]
                    for k in (
                        "group",
                        "tab",
                        "anchor",
                        "dropdown",
                        "version",
                        "language",
                    )
                    if isinstance(node.get(k), str)
                ),
                None,
            )
            for key in (
                "pages",
                "groups",
                "tabs",
                "anchors",
                "dropdowns",
                "versions",
                "languages",
            ):
                if key in node:
                    visit(node[key], trail + ([field(label)] if label else []))
        else:
            raise TypeError("Unsupported navigation entry.")

    visit(nav, [])
    return mapping


def decode(path, kind, raw):
    if kind == "image":
        mime = RASTER[PurePosixPath(path).suffix.lower()]
        valid = {
            "image/png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": raw.startswith(b"\xff\xd8\xff"),
            "image/webp": raw.startswith(b"RIFF") and raw[8:12] == b"WEBP",
        }
        if not valid[mime]:
            raise ValueError("The file does not match its image format.")
        return {"src": "data:" + mime + ";base64," + base64.b64encode(raw).decode()}
    body = raw.decode("utf-8-sig")
    if kind == "navigation":
        return navigation(body)
    path_name(path)
    text(body, "article")
    lines = body.splitlines()
    fields = {}
    if lines and lines[0] == "---":
        if "---" not in lines[1:]:
            raise ValueError("Unclosed front matter.")
        end = lines.index("---", 1)
        for line in lines[1:end]:
            match = re.fullmatch(r"(title|slug|permalink):\s*(.*?)\s*", line)
            if match:
                fields[match[1]] = match[2].strip("\"'")
        lines = lines[end + 1 :]
    visible = re.sub(r"(?ms)^(\x60{3,}|~{3,})[^\n]*\n.*?^\1\s*$", "", "\n".join(lines))
    if path.endswith(".mdx") and re.search(
        r"(?m)^\s*(import|export)\s|</?[A-Z]|\{", visible
    ):
        raise ValueError("Interactive or unsupported MDX. Review this file separately.")
    title = fields.get("title") or next(
        (s[2:].strip() for s in lines if s.startswith("# ")), PurePosixPath(path).stem
    )
    text(title, "title", 250)
    route = (
        fields.get("permalink")
        or fields.get("slug")
        or "/" + str(PurePosixPath(path).with_suffix(""))
    )
    images = []
    for alt, dest in re.findall(r"!\[([^\]]*)\]\(([^ )]+)(?:\s+[^)]*)?\)", visible):
        dest = urlsplit(dest.strip("<>"))
        if dest.scheme or dest.netloc:
            continue
        target = unquote(dest.path)
        target = posixpath.normpath(
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.join(posixpath.dirname(path), target)
        )
        if target != ".." and not target.startswith("../"):
            images.append({"alt": alt, "path": target})
    return {"title": title, "body": body, "reader_path": route, "images": images}
