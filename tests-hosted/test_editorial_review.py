"""Writing and review contracts against an isolated PostgreSQL database."""

import json
import os
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from cqa_artifacts.core import markdown_plain
from psycopg_pool import ConnectionPool
from cqa_artifacts.hosted.auth import Settings
from cqa_artifacts.hosted.editorial import Brief, compiled
from cqa_artifacts.hosted.server import create_app
from cqa_artifacts.hosted.store import PostgresStore


class GuideCompilerTests(unittest.TestCase):
    def test_tutorial_keeps_each_reviewed_attachment_with_its_instruction(self):
        # Unit fixture for Markdown formatting. No provider call or deployment attestation.
        brief = Brief(
            path="guides/example.md",
            template="Tutorial",
            audience="An owner",
            goal="Invite a member",
            prerequisite="Sign in",
            fact="Invitation pending",
            source="https://example.org/invite",
        )
        evidence = {
            "title": "Invitations",
            "media": [
                {"id": "shot", "path": "assets/shot.png", "kind": "screenshot"},
                {"id": "clip", "path": "assets/clip.mp4", "kind": "video"},
            ],
            "steps": [
                {"title": "Invite", "instruction": "Select Invite.", "media": ["shot"]},
                {
                    "title": "Confirm",
                    "instruction": "Select Confirm.",
                    "media": ["clip"],
                },
            ],
        }
        receipt = {
            "run_id": 1,
            "journey_id": "invite",
            "export_digest": "a" * 64,
            "deployment": {"application_url": "https://example.org"},
        }
        md, report = compiled(
            brief,
            {"id": "request", "title": "Invite a member"},
            {"observed_at": "2026-11-21"},
            (Path("."), evidence, receipt),
        )
        self.assertLess(
            md.index("1. " + markdown_plain("Select Invite.")),
            md.index("assets/shot.png"),
        )
        self.assertLess(
            md.index("assets/shot.png"),
            md.index("2. " + markdown_plain("Select Confirm.")),
        )
        self.assertLess(
            md.index("2. " + markdown_plain("Select Confirm.")),
            md.index("assets/clip.mp4"),
        )
        self.assertTrue(report["review_required"])


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class HostedFixture(unittest.TestCase):
    def setUp(self):
        self.org = "editorial-" + uuid4().hex
        self.url = os.environ["TEST_DATABASE_URL"]
        self.pool = ConnectionPool(self.url)
        self.addCleanup(self.pool.close)
        with self.pool.connection() as db:
            db.execute(
                "INSERT INTO docs_organizations VALUES(%s,%s)", (self.org, self.org)
            )
            for who, role in (
                ("owner", "admin"),
                ("editor", "editor"),
                ("writer", "contributor"),
            ):
                db.execute(
                    "INSERT INTO docs_memberships VALUES(%s,%s,%s)",
                    (self.org, who, role),
                )
        self.addCleanup(self.remove_org)
        self.store = PostgresStore(self.pool, self.org)
        manifest = json.loads(
            (
                Path(__file__).resolve().parents[1] / "examples/kan-pr15/manifest.json"
            ).read_text()
        )
        manifest.update(project_id="docs")
        self.store.create(manifest, "owner")
        self.base = "/api/orgs/" + self.org + "/projects/docs/"
        self.api = self.client("owner")
        self.path = "guides/invitations.md"
        self.original = "# Team invitations\n\nExisting policy."
        self.store.article(
            "docs", "owner", self.path, "Team invitations", self.original
        )
        self.brief = dict(
            path=self.path,
            audience="Owners",
            goal="Track invitations",
            prerequisite="Account",
            fact="Invitations remain pending.",
            source="https://example.org/guide",
        )

    def remove_org(self):
        with self.pool.connection() as db:
            db.execute("DELETE FROM docs_organizations WHERE id=%s", (self.org,))

    def client(self, who):
        settings = Settings(
            self.url,
            "http://127.0.0.1:8080",
            mode="development",
            auth_mode="development",
            dev_subject=who,
            dev_token="x" * 40,
        )
        client = TestClient(
            create_app(settings, self.pool),
            base_url=settings.origin,
            headers={"Authorization": "Bearer " + settings.dev_token},
        )
        self.addCleanup(client.close)
        return client

    def create(self, proposal=False, **overrides):
        event = dict(
            id=str(uuid4()),
            source="manual",
            title="Team invitations",
            text="An invitation remains pending.",
        )
        if proposal:
            event["edits"] = [
                dict(
                    path=self.path,
                    before=self.original,
                    after=self.original + "\nUpdated.",
                    reason="Invitation policy",
                )
            ]
        return self.store.ingest("docs", "owner", {**event, **overrides})["item_id"]

    def item(self, ident):
        return self.store.snapshot("docs", "owner")["items"][ident]

    def write(self, ident, mode, brief=None, version=None, code=200, api=None):
        version = self.item(ident)["version"] if version is None else version
        res = (api or self.api).post(
            self.base + "writing",
            json=dict(
                item_id=ident,
                version=version,
                mode=mode,
                brief=self.brief if brief is None else brief,
            ),
        )
        self.assertEqual(res.status_code, code, res.text)
        return res.json()


class EditorialReviewTests(HostedFixture):
    def test_profile_revision_is_owned_and_pinned_to_the_brief(self):
        url = self.base + "writing-profile"
        defaults = dict(brand="Kan", audience="Owners", voice="Business outcome", revision=0)
        editor = self.client("editor")
        self.assertEqual(editor.get(url).json(), {"revision": 0})
        self.assertEqual(editor.post(url, json=defaults).status_code, 403)
        self.assertEqual(self.api.post(url, json=defaults).json()["revision"], 1)
        self.assertEqual(self.api.post(url, json=defaults).status_code, 409)
        self.assertEqual(self.api.post(url, json=defaults | dict(revision=1, voice="Technical")).json()["revision"], 2)
        ident = self.create()
        self.write(ident, "generate", self.brief | dict(profile_revision=99), code=409)
        self.write(ident, "generate", self.brief | dict(profile_revision=1), api=editor)
        item = self.item(ident)
        self.assertEqual(item["writing"]["brief"]["profile_revision"], 1)
        self.assertIn("Customer outcome", item["changes"][0]["after"])
        self.assertIn("Kan · For Owners", item["changes"][0]["after"])
        self.assertIn(markdown_plain(self.brief["fact"]), item["changes"][0]["after"])

    def test_relative_screenshot_is_scoped_to_the_selected_revision_and_reviewer(self):
        ref = "../.gitbook/assets/invitation.jpg"
        ident = self.create(edits=[dict(path=self.path, before=self.original,
            after=self.original + "\n\n![Invitation](" + ref + ")", reason="Show the invitation")])
        params = dict(change=self.item(ident)["changes"][0]["id"], side="after", ref=ref)
        url = self.base + "writing/" + ident + "/repository-media"
        asset = Path(__file__).resolve().parents[1] / "docs/continuous-documentation/m05-evidence/article-draft.jpg"
        raw = asset.read_bytes()
        pinned = {"file": str(asset), "sha256": sha256(raw).hexdigest()}
        config = {"review_media": {ident: {".gitbook/assets/invitation.jpg": pinned}}}
        with patch("cqa_artifacts.hosted.editorial.binding", return_value=config):
            response = self.api.get(url, params=params)
            self.assertEqual((response.status_code, response.content), (200, raw))
            self.assertEqual(response.headers["content-type"], "image/jpeg")
            for overrides in ({"side": "before"}, {"change": "other"}, {"ref": "../other.jpg"}, {"ref": "//["}):
                self.assertEqual(self.api.get(url, params={**params, **overrides}).status_code, 404)
            self.assertEqual(self.client("writer").get(url, params=params).status_code, 404)
            pinned["sha256"] = "0" * 64
            self.assertGreaterEqual(self.api.get(url, params=params).status_code, 400)

    def test_partial_round_stale_submit_and_preserved_baseline(self):
        ident = self.create()
        saved = self.write(ident, "save", {**self.brief, "fact": ""})
        self.write(ident, "generate", {**self.brief, "fact": ""}, code=409)
        self.write(ident, "generate", version=1, code=409)
        current = self.write(ident, "generate", version=saved["version"])
        self.assertEqual(
            current, self.write(ident, "generate", version=saved["version"])
        )
        self.assertEqual(current, self.write(ident, "generate"))
        self.assertEqual(current, self.write(ident, "save"))
        item = self.item(ident)
        self.assertEqual(len(item["writing_history"]), 1)
        self.assertEqual(item["changes"][0]["before"], self.original)
        self.assertIn(self.original, item["changes"][0]["after"])
        self.assertEqual(
            item["changes"][0]["after"].count(markdown_plain(self.brief["fact"])), 1
        )
        self.write(ident, "generate", {**self.brief, "fact": "A newer policy applies."})
        item = self.item(ident)
        self.assertNotIn(
            markdown_plain(self.brief["fact"]), item["changes"][0]["after"]
        )
        self.assertIn(
            markdown_plain("A newer policy applies."), item["changes"][0]["after"]
        )
        self.assertEqual(
            self.store.snapshot("docs", "owner")["articles"][self.path]["body"],
            self.original,
        )

    def test_no_change_requires_reason_and_skips_churn(self):
        ident = self.create()
        self.write(ident, "no_change", {**self.brief, "source": ""}, code=409)
        result = self.write(ident, "no_change")
        self.assertEqual(result, self.write(ident, "no_change"))
        self.assertEqual(self.item(ident)["changes"], [])
        for args in (
            dict(requires_capture=True),
            dict(agent_questions=["Confirm the role."]),
        ):
            self.write(self.create(**args), "no_change", code=409)

    def test_tutorial_requires_reviewed_project_capture(self):
        ident = self.create(requires_screenshots=True)
        for extra in ({}, {"capture": str(uuid4())}):
            self.write(
                ident,
                "generate",
                {**self.brief, "template": "Tutorial", **extra},
                code=409,
            )
        self.assertEqual(self.item(ident)["version"], 1)
        self.write(ident, "save", api=self.client("writer"), code=409)

    def test_handoff_revokes_former_reviewer_and_preserves_decisions(self):
        ident = self.create(proposal=True)
        self.store.review("docs", "owner", ident, 1, "assign", assignee="writer")
        writer = self.client("writer")

        def review(version, action, data=None):
            return writer.post(
                self.base + "review",
                json=dict(
                    item_id=ident, version=version, action=action, data=data or {}
                ),
            )

        note = dict(assignee="editor", note="Ready for final review")
        self.assertEqual(review(2, "handoff", note).status_code, 409)
        self.assertEqual(
            review(
                2, "comment", dict(text="Checked the wording", change_id="1")
            ).status_code,
            200,
        )
        self.assertEqual(review(3, "accept_item").status_code, 200)
        res = review(4, "handoff", note)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertNotIn("changes", res.json())
        self.assertEqual(review(4, "handoff", note).status_code, 409)
        self.assertEqual(writer.get(self.base + "state").json()["items"], {})
        self.assertEqual(
            writer.get(self.base + "writing/" + ident + "/figures/no/such").status_code,
            404,
        )
        self.assertEqual(
            writer.post(self.base + "bundle", json=dict(item_id=ident)).status_code, 409
        )
        item = self.item(ident)
        self.assertEqual(
            (
                len(item["handoffs"]),
                item["comments"][0]["change_id"],
                item["changes"][0]["decision"],
            ),
            (1, "1", "accepted"),
        )
        self.assertEqual(item["assignee"], "editor")
        self.assertIsNone(item["delivery"])

    def test_page_conflict_archive_recovery_and_out_of_scope_requests(self):
        ids = [self.create(proposal=True) for _ in range(11)]
        self.store.review("docs", "owner", ids[1], 1, "priority", priority="high")
        rows = [dict(id=i, version=1) for i in ids]
        self.assertEqual(
            self.api.post(self.base + "review-page", json=dict(items=rows)).status_code,
            422,
        )
        r = self.api.post(self.base + "review-page", json=dict(items=rows[:10]))
        self.assertEqual(
            [p["id"] for p in r.json()["results"] if not p["accepted"]], [ids[1]]
        )
        self.assertEqual(self.item(ids[10])["changes"][0]["decision"], "pending")
        self.assertEqual(self.item(ids[1])["changes"][0]["decision"], "pending")
        for ver, act, status in (
            (2, "archive", "archived"),
            (3, "restore", "open"),
            (4, "resolve", "resolved"),
        ):
            item = self.store.review("docs", "owner", ids[1], ver, act)
            self.assertEqual(item["status"], status)
            self.assertIsNone(item["delivery"])
