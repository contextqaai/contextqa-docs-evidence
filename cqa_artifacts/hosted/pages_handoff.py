"""Open a reviewable Pages PR for one saved, explicitly public guide version."""

import base64
from html import escape, unescape
import json
import posixpath
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends
import httpx
import mistune
from pydantic import BaseModel, Field

from ..core import Rejected, digest
from ..editions import MEDIA
from ..loop import fingerprint
from .destinations import manifest_files, pages_configuration
from .github_intake import BoundConnection, github_access, github_get
from .store import PostgresStore
from .onboarding import PREFIX, admin, binding, setup
from .repository_docs import sha

PRIVATE = re.compile(
    r"<!--|\b(?:internal[- ]only|internal note|do not publish|confidential)\b|"
    r"(?:api[_ -]?key|access[_ -]?token|password|secret|authorization|cookie)\s*[:=]\s*\S|"
    r"\b(?:Bearer\s+\S+|token_[\w-]+\.[\w-]+|gh[pousr]_[\w]+|github_pat_[\w]+|sk-[\w-]{12,})|"
    r"-----BEGIN [\w ]*PRIVATE KEY-----|x-amz-signature=|https?://[^\s/]*slack\.com/",
    re.I,
)
LIMIT = 16 * 1024 * 1024


class Selection(BaseModel):
    path: str = Field(min_length=1, max_length=250)
    version: str = Field(pattern="^[0-9a-f]{64}$")


class PublicDecision(Selection):
    preview: str = Field(pattern="^[0-9a-f]{64}$")
    approved_for_public: bool


class GuideRenderer(mistune.HTMLRenderer):
    def __init__(self, path, media):
        super().__init__(escape=True)
        self.path = path
        self.media = media
        self.used = set()

    def asset(self, url):
        path = posixpath.normpath(posixpath.join(posixpath.dirname(self.path), url))
        if path not in self.media:
            raise Rejected(
                "Review the guide links. Public output supports its approved evidence and section anchors."
            )
        self.used.add(path)
        return self.media[path]

    def image(self, text, url, title=None):
        name = self.asset(url)
        if not name.endswith((".png", ".jpg", ".webp")):
            raise Rejected("Expected a reviewed screenshot.")
        caption = escape(unescape(re.sub(r"<[^>]*>", "", text)))
        return f'<a href="{name}" aria-label="Open original screenshot"><img src="{name}" alt="{caption}"></a>'

    def link(self, text, url, title=None):
        if re.fullmatch(r"#[A-Za-z0-9_-]+", url):
            return f'<a href="{url}">{text}</a>'
        name = self.asset(url)
        if name.endswith((".mp4", ".webm")):
            return (
                f'<video controls preload="metadata" src="{name}"></video> '
                f'<a href="{name}">{text}</a>'
            )
        return f'<a href="{name}">{text}</a>'


def guide_files(path, version, body, media, read_media, namespace):
    if PRIVATE.search(path + "\n" + body) or re.search(
        r"(?:^|/)(?:internal|private|drafts?)(?:/|$)", path, re.I
    ):
        raise Rejected(
            "Public disclosure review found restricted content. Edit and approve a new guide version."
        )
    folder = "sofa/" + fingerprint([namespace, path])[:32] + "/"
    files, names = {}, {}
    total = 0
    for m in media:
        match = MEDIA.fullmatch(m["path"])
        if not match or match[2] != m["digest"]:
            raise Rejected("Invalid saved evidence reference.")
        name = match[2] + "." + match[3]
        raw = read_media(match[2])
        total += len(raw)
        if digest(raw) != match[2] or total > LIMIT or len(names) >= 28:
            raise Rejected(
                "Evidence exceeds the public bundle limits or differs from its approved bytes."
            )
        names[m["path"]] = name
        files[folder + name] = raw
    renderer = GuideRenderer(path, names)
    html = mistune.create_markdown(renderer=renderer)(body)
    if not names or renderer.used != set(names):
        raise Rejected(
            "The published guide must reference every selected evidence file."
        )
    title = next((s[2:].strip() for s in body.splitlines() if s.startswith("# ")), path)
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; img-src &#39;self&#39;; media-src &#39;self&#39;; style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;">'
        "<title>"
        + escape(title)
        + "</title><style>main{max-width:76rem;margin:auto;padding:1rem;font:1rem/1.55 system-ui}"
        'img,video{max-width:100%;height:auto}pre{overflow:auto}</style><main><a href="../../">All guides</a>'
        + html
        + "<footer>Guide revision "
        + version
        + "</footer></main></html>"
    )
    guide = folder + "index.html"
    files[guide] = page.encode()
    return files, guide, title


def file_at(config, repo, path, revision, limit):
    obj = github_get(config, repo + "/contents/" + path, {"ref": revision})
    try:
        if obj["type"] != "file" or obj["encoding"] != "base64" or obj["size"] > limit:
            raise ValueError()
        return base64.b64decode(obj["content"].replace("\n", ""), validate=True)
    except (KeyError, ValueError):
        raise Rejected("Invalid file in the Pages publishing source.") from None


def prepare(config, cfg, selection, content, guide, title):
    repo = "/repos/" + cfg["docs_repo"]
    site = pages_configuration(cfg, github_get(config, repo + "/pages"))
    head = github_get(config, repo + "/commits/" + quote(cfg["branch"], safe=""))
    base = sha(head["sha"])
    root = site["root"].strip("/")
    prefix = root + "/" if root else ""
    raw = file_at(config, repo, prefix + "release.json", base, 32768)
    existing = manifest_files(raw)
    index = file_at(config, repo, prefix + "index.html", base, 1024 * 1024)
    if digest(index) != existing["index.html"]:
        raise Rejected("The Pages landing page differs from its manifest.")
    # Preserve the existing site. Keep each guide's media inside its own directory.
    folder = guide.rsplit("/", 1)[0] + "/"
    removed = sorted(k for k in existing if k.startswith(folder) and k not in content)
    unchanged = not removed and all(
        existing.get(k) == digest(v) for k, v in content.items()
    )
    original_index = index
    index = index.decode("utf-8")
    marker = "<!-- sofa-guide " + guide + " -->"
    end = "<!-- end sofa-guide -->"
    link = marker + '<p><a href="' + guide + '">' + escape(title) + "</a></p>" + end
    if marker in index:
        start = index.index(marker)
        if end not in index[start:]:
            raise Rejected("Repair the managed guide link in the Pages index.")
        index = index[:start] + link + index[index.index(end, start) + len(end) :]
    elif index.count("</main>") == 1:
        index = index.replace("</main>", link + "</main>")
    else:
        raise Rejected("The Pages index needs a main element for the guide link.")
    files = {**content, "index.html": index.encode()}
    hashes = {k: v for k, v in existing.items() if k not in removed}
    hashes.update({k: digest(v) for k, v in files.items()})
    manifest = {**json.loads(raw), "edition": selection.version, "files": hashes}
    files["release.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    manifest_files(files["release.json"])
    receipt = fingerprint(
        [
            cfg["docs_repo"],
            cfg["branch"],
            root,
            base,
            selection.version,
            digest(files["release.json"]),
        ]
    )
    return dict(
        repository=cfg["docs_repo"],
        branch=cfg["branch"],
        base=base,
        root=prefix,
        tree=sha(head["commit"]["tree"]["sha"]),
        preview=receipt,
        guide=guide,
        files=files,
        removed=removed,
        unchanged=unchanged and files["index.html"] == original_index,
    )


def write(config, repo, endpoint, payload):
    try:
        response = httpx.post(
            "https://api.github.com" + repo + endpoint,
            headers={"Authorization": "Bearer " + config["installation_token"]},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except (ValueError, httpx.HTTPError):
        raise Rejected(
            "GitHub did not confirm the write. Reopen the same preview to reconcile its draft branch."
        ) from None


def open_draft(config, candidate):
    repo_name, base = candidate["repository"], candidate["base"]
    repo = "/repos/" + repo_name
    branch = "sofa-pages/" + candidate["preview"]
    head = repo_name.split("/")[0] + ":" + branch
    entries = []
    for path, raw in sorted(candidate["files"].items()):
        blob = write(
            config,
            repo,
            "/git/blobs",
            {"content": base64.b64encode(raw).decode(), "encoding": "base64"},
        )
        entries.append(
            dict(
                path=candidate["root"] + path,
                mode="100644",
                type="blob",
                sha=sha(blob["sha"]),
            )
        )
    entries.extend(
        dict(path=candidate["root"] + path, mode="100644", type="blob", sha=None)
        for path in candidate["removed"]
    )
    tree = sha(
        write(
            config,
            repo,
            "/git/trees",
            {"base_tree": candidate["tree"], "tree": entries},
        )["sha"]
    )
    refs = github_get(config, repo + "/git/matching-refs/heads/" + branch)
    ref = next((r for r in refs if r["ref"] == "refs/heads/" + branch), None)
    if ref:
        commit = sha(ref["object"]["sha"])
        prior = github_get(config, repo + "/git/commits/" + commit)
        if prior["tree"]["sha"] != tree or [p["sha"] for p in prior["parents"]] != [
            base
        ]:
            raise Rejected(
                "The existing draft branch has changed. Review it on GitHub."
            )
    else:
        commit = sha(
            write(
                config,
                repo,
                "/git/commits",
                {
                    "tree": tree,
                    "parents": [base],
                    "message": "Publish the reviewed SoFa Docs guide",
                },
            )["sha"]
        )
        write(config, repo, "/git/refs", {"ref": "refs/heads/" + branch, "sha": commit})
    params = {"head": head, "base": candidate["branch"], "state": "all"}
    prior_prs = github_get(config, repo + "/pulls", params)
    if prior_prs:
        pr = prior_prs[0]
    else:
        if (
            github_get(
                config, repo + "/commits/" + quote(candidate["branch"], safe="")
            )["sha"]
            != base
        ):
            raise Rejected("The publication branch advanced. Review a new preview.")
        pr = write(
            config,
            repo,
            "/pulls",
            {
                "head": branch,
                "base": candidate["branch"],
                "draft": True,
                "title": "Publish reviewed SoFa Docs guide",
                "body": "Reviewed public guide and its selected ContextQA evidence. Preview digest: "
                + candidate["preview"],
            },
        )
    if (
        pr["head"]["sha"] != commit
        or pr["head"]["repo"]["full_name"] != repo_name
        or pr["base"]["ref"] != candidate["branch"]
    ):
        raise Rejected("The draft PR no longer matches the public disclosure decision.")
    return {
        "url": "https://github.com/" + repo_name + "/pull/" + str(int(pr["number"])),
        "state": pr["state"],
    }


def router(pool, auth):
    routes = APIRouter()

    def handoff(org, project, actor, selection, decision=None):
        with pool.connection() as db:
            admin(db, org, actor)
            cfg = setup(db, org, project)
            if not cfg["connected"]:
                raise Rejected("Connect the Pages publishing destination first.")
            row = db.execute(
                """SELECT v.body,v.media FROM docs_guide_versions v JOIN docs_guide_heads h
                USING(organization_id,project_id,path,digest) WHERE v.organization_id=%s AND v.project_id=%s
                AND v.path=%s AND v.digest=%s FOR SHARE OF h""",
                (org, project, selection.path, selection.version),
            ).fetchone()
            if not row:
                raise Rejected("Select the current saved, approved guide.")

            def read_media(mid):
                row = db.execute(
                    "SELECT content FROM docs_guide_media WHERE organization_id=%s AND project_id=%s AND digest=%s",
                    (org, project, mid),
                ).fetchone()
                if not row:
                    raise Rejected("The saved evidence file is unavailable.")
                return bytes(row[0])

            files, guide, title = guide_files(
                selection.path, selection.version, *row, read_media, [org, project]
            )
            permissions = {"contents": "read", "pages": "read"}
            if decision:
                if not decision.approved_for_public:
                    raise Rejected(
                        "Review the guide and its original media for public disclosure."
                    )
                permissions.update(contents="write", pull_requests="write")
            app = binding(org, project).get("pages_github_app") or {}
            if (
                app.get("repository") != cfg["docs_repo"]
                or app.get("branch") != cfg["branch"]
                or not app.get("app_private_key")
                or not app.get("app_id")
                or not app.get("installation_id")
                or app.get("installation_token")
            ):
                raise Rejected(
                    "Configure the Pages GitHub App for this repository and publishing branch."
                )
            config = github_access(
                app, permissions=permissions, repository=cfg["docs_repo"].split("/")[-1]
            )
            candidate = prepare(config, cfg, selection, files, guide, title)
            if decision is None:
                return {
                    k: candidate[k]
                    for k in (
                        "repository",
                        "branch",
                        "base",
                        "preview",
                        "guide",
                        "unchanged",
                    )
                } | {"media_count": len(row[1])}
            if decision.preview != candidate["preview"]:
                raise Rejected(
                    "The destination or release changed. Review a new public preview."
                )
            if candidate["unchanged"]:
                raise Rejected(
                    "This guide revision is already present in the selected branch."
                )
            receipt = open_draft(config, candidate)
            store = PostgresStore(BoundConnection(db), org)
            with store.transaction(project) as state:
                store.log(
                    state,
                    actor,
                    "Public guide PR "
                    + receipt["url"]
                    + " at preview "
                    + candidate["preview"],
                    selection.path,
                )
            return receipt

    @routes.post(PREFIX + "/pages/preview")
    def preview(org: str, project: str, body: Selection, actor=Depends(auth)):
        return handoff(org, project, actor, body)

    @routes.post(PREFIX + "/pages/draft-pr")
    def publish(org: str, project: str, body: PublicDecision, actor=Depends(auth)):
        return handoff(org, project, actor, body, body)

    return routes
