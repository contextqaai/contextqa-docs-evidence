"""Inspect the configured documentation destination using the workspace installation."""

import base64
import re
from urllib.parse import quote, urlsplit
from fastapi import APIRouter, Depends
from ..core import Rejected
from .onboarding import PREFIX, setup, binding, admin
from .github_intake import github_get
from .repository_docs import sha


def configured_root(raw):
    # Allow only a plain scalar path. Unknown YAML features need explicit review.
    if len(raw) > 65536:
        raise Rejected("GitBook configuration is too large.")
    lines = [line for line in raw.splitlines() if re.match(r"^root\s*:", line)]
    if not lines:
        return ""
    if len(lines) != 1:
        raise Rejected("Ambiguous GitBook content root.")
    m = re.fullmatch(r"root\s*:\s*['\"]?([\w./-]+)['\"]?\s*(?:#.*)?", lines[0])
    if not m:
        raise Rejected("Review the GitBook root expression.")
    value = m[1].removeprefix("./").rstrip("/")
    if value in (".", ""):
        return ""
    if value.startswith("/") or any(
        p in ("", ".", "..", ".git", ".github") for p in value.split("/")
    ):
        raise Rejected("Invalid GitBook content root.")
    return value


def pages_configuration(cfg, site):
    address = site.get("html_url", "")
    parsed = urlsplit(address)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise Rejected("GitHub returned an invalid Pages site address.")
    source = site.get("source") or {}
    if site.get("build_type") == "workflow":
        raise Rejected("This check supports branch publishing. The Pages site uses GitHub Actions.")
    if site.get("build_type") != "legacy" or not isinstance(source, dict):
        raise Rejected("GitHub did not identify a branch publishing source.")
    path = source.get("path")
    if (source.get("branch") != cfg["branch"] or path not in ("/", "/docs")
            or path.strip("/") != cfg["docs_root"].strip("/")):
        raise Rejected("The Pages publishing branch or folder differs from the saved documentation scope.")
    if site.get("public") is not True:
        raise Rejected("GitHub has not confirmed this destination is public.")
    return dict(repository=cfg["docs_repo"], branch=cfg["branch"], root=path,
                url=address, status="configuration_verified", public_site_verified=False)


def router(pool, auth):
    r = APIRouter()

    @r.post(PREFIX + "/pages/check")
    def check_pages(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg = setup(db, org, project)
        if not cfg["connected"]:
            raise Rejected("Connect the documentation repository first.")
        config = binding(org, project)
        site = github_get(config, "/repos/" + cfg["docs_repo"] + "/pages")
        return pages_configuration(cfg, site)

    @r.post(PREFIX + "/gitbook/check")
    def check(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg = setup(db, org, project)
            if not cfg["connected"]:
                raise Rejected("Connect the documentation repository first.")
            binding_cfg = binding(org, project)
            repo = "/repos/" + cfg["docs_repo"]
            revision = sha(
                github_get(
                    binding_cfg, repo + "/commits/" + quote(cfg["branch"], safe="")
                )["sha"]
            )
            file = github_get(
                binding_cfg, repo + "/contents/.gitbook.yaml", {"ref": revision}
            )
            if file.get("type") != "file" or file.get("encoding") != "base64":
                raise Rejected(
                    "Cannot read the GitBook configuration at this revision."
                )
            try:
                root = configured_root(base64.b64decode(file["content"]).decode())
            except (KeyError, ValueError, UnicodeError):
                raise Rejected("Invalid GitBook configuration.") from None
            if root != cfg["docs_root"].strip("/"):
                raise Rejected(
                    "GitBook root and the selected documentation folder differ."
                )
            return dict(
                repository=cfg["docs_repo"],
                branch=cfg["branch"],
                root=root,
                revision=revision,
                status="repository_verified",
                public_site_verified=False,
            )

    return r
