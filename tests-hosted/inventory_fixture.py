"""Synthetic Git objects served at the GitHub REST boundary of import tests."""

import base64
import hashlib
import json


def blob_id(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class Repository:
    def __init__(self, image=None, invalid=False):
        self.files = {
            "admin/setup.md": b"# Getting started\n\nOpen organization settings to configure your team.\n",
            "teams/setup.mdx": b"---\nslug: /team-onboarding\n---\n# Getting started\n\nInvite a teammate, then ask them to accept the invitation.\n\n![Invitation sequence](../images/invitation.png)\n",
            "images/invitation.png": image
            or base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJWQAAAAASUVORK5CYII="
            ),
            "docs.json": json.dumps(
                {
                    "navigation": {
                        "groups": [
                            {"group": "Administration", "pages": ["admin/setup"]},
                            {"group": "Team guides", "pages": ["teams/setup"]},
                        ]
                    }
                }
            ).encode(),
        }
        if invalid:
            self.files.update(
                {
                    "legacy.mdx": b"# Legacy\n\n<InteractiveDemo />\n",
                    "mint.json": b"{invalid",
                }
            )
        self.truncate = False
        self.fail_blob = False

    def get(self, config, path, params=None):
        from fastapi import HTTPException

        if "/commits/" in path:
            return {
                "sha": blob_id(b"".join(self.files.values())),
                "commit": {"tree": {"sha": "1" * 40}},
            }
        if "/git/trees/" in path:
            if path.endswith("1" * 40):
                return {
                    "truncated": False,
                    "tree": [{"type": "tree", "path": "docs", "sha": "2" * 40}],
                }
            if self.truncate:
                self.truncate = False
                return {"truncated": True, "tree": []}
            return {
                "truncated": False,
                "tree": [
                    {
                        "mode": "100644",
                        "type": "blob",
                        "path": p,
                        "sha": blob_id(b),
                        "size": len(b),
                    }
                    for p, b in self.files.items()
                ],
            }
        if self.fail_blob:
            self.fail_blob = False
            raise HTTPException(
                502, "Repository read interrupted. Resume reading files to continue."
            )
        raw = next(raw for raw in self.files.values() if path.endswith(blob_id(raw)))
        return {"encoding": "base64", "content": base64.b64encode(raw).decode()}


def connect(db, org, project, repo):
    db.execute(
        """INSERT INTO docs_setup(organization_id,project_id,docs_repo,branch,docs_root,connected)
        VALUES(%s,%s,%s,'main','docs',true)""",
        (org, project, repo),
    )
