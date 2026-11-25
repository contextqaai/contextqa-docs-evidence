"""Build private walkthrough scenes from one saved edition's approved figures."""

import posixpath
import re
from urllib.parse import urlsplit

import mistune

from ..editions import MEDIA


def _caption(node):
    if node["type"] in {"text", "codespan"}:
        return node["raw"]
    return "".join(_caption(child) for child in node.get("children", []))


def walkthrough_scenes(path, body, media):
    approved = {}
    for row in media:
        match = MEDIA.fullmatch(row.get("path", ""))
        if (match and match[2] == row.get("digest")
                and row.get("kind") == ("video" if match[3] in {"webm", "mp4"} else "screenshot")
                and row.get("run") and row.get("step") and row.get("journey") and row.get("revision")):
            approved[row["path"]] = row

    scenes = []
    heading = ""
    def visit(node):
        nonlocal heading
        kind = node["type"]
        if kind == "heading":
            heading = _caption(node).strip()
        if kind in {"link", "image"}:
            target = node["attrs"]["url"]
            try:
                url = urlsplit(target)
            except ValueError:
                return
            if not (url.scheme or url.netloc or url.query or url.fragment or target.startswith("/")):
                row = approved.get(posixpath.normpath(posixpath.join(posixpath.dirname(path), target)))
                if row:
                    scenes.append({
                        **{k: row[k] for k in ("digest", "kind", "journey", "revision", "run", "step")},
                        "caption": _caption(node).strip() or heading or "Reviewed evidence",
                    })
                    return
        for child in node.get("children", []):
            visit(child)

    visible = re.sub(r"<!--.*?(?:-->|$)", "", body, flags=re.DOTALL)
    for node in mistune.create_markdown(renderer="ast")(visible):
        visit(node)
    return scenes
