"""Provision the isolated documentation workshop for a local development identity."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from psycopg_pool import ConnectionPool
from psycopg.types.json import Jsonb
from cqa_artifacts.hosted.github_intake import BoundConnection
from cqa_artifacts.hosted.store import PostgresStore
from cqa_artifacts.loop import fingerprint


def seed(pool, subject):
    repo = Path(__file__).resolve().parents[2]
    org, project = "docs-workshop", "guides"
    path = "guides/invitations.md"
    manifest = json.loads((repo / "examples/kan-pr15/manifest.json").read_text())
    manifest.update(
        project_id=project,
        name="Documentation workshop",
        repository="sample/invitations",
        application_url="https://example.org/invitations",
        sections=[
            dict(
                id="invitations",
                path=path,
                title="Team invitations",
                owner=subject,
                module_ids=["invites"],
                code_paths=["ui/invitations.tsx"],
                keywords=["invite"],
            )
        ],
    )
    with pool.connection() as db:
        existing = db.execute(
            "SELECT id FROM docs_organizations WHERE id=%s", (org,)
        ).fetchone()
        if existing:
            row = db.execute(
                "SELECT state->'manifest'->>'name' FROM docs_projects WHERE organization_id=%s AND id=%s",
                (org, project),
            ).fetchone()
            if not row or row[0] != "Documentation workshop":
                raise ValueError("Reserved workshop name is already in use.")
            return
        db.execute(
            "INSERT INTO docs_organizations(id,name) VALUES(%s,'Documentation workshop example')",
            (org,),
        )
        db.execute(
            "INSERT INTO docs_memberships VALUES(%s,%s,'admin'),(%s,'workshop-reviewer','editor')",
            (org, subject, org),
        )
        store = PostgresStore(BoundConnection(db), org)
        store.create(manifest, subject)
        original = "# Team invitations\n\nA workspace owner can invite colleagues."
        store.article(project, subject, path, "Team invitations", original)
        event = {
            "source": "manual",
            "text": "Invitations remain pending until accepted.",
            "source_url": "https://example.org/invitations",
            "module_ids": ["invites"],
        }
        store.ingest(
            project,
            subject,
            {**event, "id": "workshop-writing", "title": "Write the invitation guide"},
        )
        store.ingest(
            project,
            subject,
            {
                **event,
                "id": "workshop-review",
                "title": "Hand off the invitation review",
                "edits": [
                    dict(
                        path=path,
                        before=original,
                        after=original
                        + "\n\nInvitations remain pending until accepted.",
                        reason=event["text"],
                    )
                ],
            },
        )
        # Only the screenshot and run/step provenance are live evidence. The version is a workshop seed.
        folder = repo / "docs/continuous-documentation/m05-evidence"
        provenance = json.loads(
            (folder / "writing-desktop-provenance.json").read_text()
        )
        image = (folder / "article-draft.jpg").read_bytes()
        mid = hashlib.sha256(image).hexdigest()
        if mid != next(
            a["sha256"]
            for a in provenance["assets"]
            if a["file"] == "article-draft.jpg"
        ):
            raise ValueError("Workshop screenshot differs from its receipt.")
        group = fingerprint(provenance)
        target = "evidence/" + group + "/assets/" + mid + ".jpg"
        article = "guides/review-invitations.md"
        text = (
            "# Review the invitation guide\n\nOpen Writing, complete the brief, select Generate draft and open Article.\n\n![Reviewed invitation article](../"
            + target
            + ")\n"
        )
        version = fingerprint([article, text, mid])
        media = [
            dict(
                path=target,
                kind="screenshot",
                digest=mid,
                export=group,
                journey="review-invitation-guide",
                run=provenance["result_id"],
                step=provenance["step_result_id"],
                revision="workshop fixture",
            )
        ]
        src = dict(
            title="Review the invitation guide",
            fixture=True,
            source_url="https://ship-5.contextqa.com/run-result-view?testCaseId=215&runResultId=483",
        )
        db.execute(
            """INSERT INTO docs_guide_versions(organization_id,project_id,path,digest,item_id,approval,body,media,source,actor)
            VALUES(%s,%s,%s,%s,'workshop','workshop-fixture',%s,%s,%s,%s)""",
            (org, project, article, version, text, Jsonb(media), Jsonb(src), subject),
        )
        db.execute(
            "INSERT INTO docs_guide_heads VALUES(%s,%s,%s,%s)",
            (org, project, article, version),
        )
        db.execute(
            "INSERT INTO docs_guide_media VALUES(%s,%s,%s,'image/jpeg',%s)",
            (org, project, mid, image),
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    args = p.parse_args()
    with ConnectionPool(os.environ["DATABASE_URL"]) as pool:
        seed(pool, args.subject)
