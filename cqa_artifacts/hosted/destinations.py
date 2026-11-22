"""Inspect the configured documentation destination using the workspace installation."""

import base64
import hashlib
import json
import httpx
import re
from urllib.parse import quote, urlsplit
from fastapi import APIRouter, Depends
from ..core import Rejected
from .onboarding import PREFIX, setup, binding, admin
from .github_intake import github_access, github_get
from .repository_docs import sha
from .publication import fetch_public


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


def manifest_files(raw):
    try:
        manifest = json.loads(raw)
        files = manifest["files"]
        if not isinstance(files, dict) or "index.html" not in files or len(files) > 32:
            raise ValueError()
        for rel, digest in files.items():
            if (len(rel) > 250 or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*(?:/[A-Za-z0-9_-][A-Za-z0-9._-]*)*", rel)
                    or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise ValueError()
        return files
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Rejected("Invalid Pages release manifest.") from None


def verify_pages_release(config, cfg):
    repo = "/repos/" + cfg["docs_repo"]
    site = pages_configuration(cfg, github_get(config, repo + "/pages"))
    owner, name = cfg["docs_repo"].lower().split("/")
    host = owner + ".github.io"
    base = "https://" + host + ("/" if name == host else "/" + name + "/")
    if site["url"].rstrip("/").lower() != base.rstrip("/"):
        raise Rejected("Public file verification currently supports the default github.io address.")
    base = site["url"].rstrip("/") + "/"
    ref_path = repo + "/commits/" + quote(cfg["branch"], safe="")
    revision = sha(github_get(config, ref_path)["sha"])
    build = github_get(config, repo + "/pages/builds/latest")
    if build.get("status") != "built" or build.get("commit") != revision:
        raise Rejected("Wait for Pages to build the selected documentation commit.")
    root = site["root"].strip("/")
    path = (root + "/" if root else "") + "release.json"
    obj = github_get(config, repo + "/contents/" + path, {"ref": revision})
    try:
        if obj.get("type") != "file" or obj.get("encoding") != "base64" or len(obj["content"]) > 32768:
            raise ValueError()
        raw = base64.b64decode(obj["content"].replace("\n", ""), validate=True)
        files = manifest_files(raw)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Rejected("The selected revision needs a valid release.json with public file digests.") from None
    try:
        fetch_public(base + "release.json", hashlib.sha256(raw).hexdigest())
        for rel, digest in files.items():
            fetch_public(base + rel, digest)
    except httpx.HTTPError:
        raise Rejected("Could not read the deployed Pages files. Retry after deployment.") from None
    if github_get(config, ref_path)["sha"] != revision:
        raise Rejected("The documentation branch advanced during verification. Check the new revision.")
    return dict(**site, revision=revision, build=build.get("url"), verified_files=list(files),
                files_verified=True)


def pages_reader(org, project, cfg):
    config = binding(org, project)
    app = config.get("pages_github_app")
    if app:
        if (app.get("repository"), app.get("branch")) != (cfg["docs_repo"], cfg["branch"]):
            raise Rejected("The Pages installation differs from the saved repository or branch.")
        config = app
    return github_access(config, permissions={"contents":"read", "pages":"read"}, repository=cfg["docs_repo"].split("/")[-1])


def router(pool, auth):
    r = APIRouter()

    @r.post(PREFIX + "/pages/check")
    def check_pages(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg = setup(db, org, project)
        if not cfg["connected"]:
            raise Rejected("Connect the documentation repository first.")
        config = pages_reader(org, project, cfg)
        site = github_get(config, "/repos/" + cfg["docs_repo"] + "/pages")
        return pages_configuration(cfg, site)

    @r.post(PREFIX + "/pages/verify")
    def verify_pages(org: str, project: str, actor=Depends(auth)):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg = setup(db, org, project)
        if not cfg["connected"]:
            raise Rejected("Connect the documentation repository first.")
        return verify_pages_release(pages_reader(org, project, cfg), cfg)

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
