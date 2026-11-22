import base64
import json
import unittest
from unittest.mock import patch

from cqa_artifacts.core import Rejected, digest
from cqa_artifacts.hosted import pages_handoff as pages
from cqa_artifacts.hosted.onboarding import setup
from test_guide_library import GuideLibraryTests as _GuideFixtures
from test_editorial_review import HostedFixture


# Reuse the real saved approval flow without collecting the fixture's other tests.
class PagesHandoffTests(HostedFixture):
    verified_fixture = _GuideFixtures.verified_fixture
    request_with_evidence = _GuideFixtures.request_with_evidence
    library_save = _GuideFixtures.library_save

    def setUp(self):
        super().setUp()
        with self.pool.connection() as db:
            setup(db, self.org, "docs")
            db.execute(
                """UPDATE docs_setup SET connected=true,docs_repo='sample/repo',
                branch='staging-publish',docs_root='docs' WHERE organization_id=%s AND project_id='docs'""",
                (self.org,),
            )
        self.head = "a" * 40
        self.tree = "b" * 40
        self.commit = "c" * 40
        self.ref = None
        self.prs = []
        self.posts = []
        self.index = b"<main><p>Other articles</p></main>"
        policy = dict(
            repository="sample/repo",
            branch="staging-publish",
            app_id="1",
            installation_id="1",
            app_private_key="fixture",
        )
        self.binding = patch.object(
            pages, "binding", return_value={"pages_github_app": policy}
        ).start()
        self.access = patch.object(pages, "github_access", return_value={}).start()
        self.addCleanup(patch.stopall)
        self.patch = patch.object(pages, "github_get", self.get)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.writer = patch.object(pages, "write", self.post)
        self.writer.start()
        self.addCleanup(self.writer.stop)

    def get(self, config, path, params=None):
        if path.endswith("/pages"):
            return dict(
                html_url="https://sample.github.io/repo/",
                public=True,
                build_type="legacy",
                source=dict(branch="staging-publish", path="/docs"),
            )
        if path.endswith("/commits/staging-publish"):
            return {"sha": self.head, "commit": {"tree": {"sha": self.tree}}}
        if "/contents/" in path:
            raw = (
                self.index
                if path.endswith("index.html")
                else json.dumps({"files": {"index.html": digest(self.index)}}).encode()
            )
            return dict(
                size=len(raw),
                content=base64.b64encode(raw).decode(),
                type="file",
                encoding="base64",
            )
        if "/matching-refs/" in path:
            return [self.ref] if self.ref else []
        if path.endswith("/git/commits/" + self.commit):
            return dict(tree={"sha": self.tree}, parents=[{"sha": self.head}])
        if path.endswith("/pulls"):
            return self.prs
        raise AssertionError(path)

    def post(self, config, repo, endpoint, data):
        self.posts.append((endpoint, data))
        if endpoint == "/git/refs":
            self.ref = dict(ref=data["ref"], object={"sha": data["sha"]})
        if endpoint == "/pulls":
            self.prs = [
                dict(
                    number=42,
                    state="open",
                    head={"sha": self.commit, "repo": {"full_name": "sample/repo"}},
                    base={"ref": "staging-publish"},
                )
            ]
            return self.prs[0]
        return {"sha": self.commit if endpoint == "/git/commits" else self.tree}

    def test_draft_uses_saved_bytes_and_retry_reconciles(self):
        _, version, mid = self.library_save()
        body = dict(path=self.path, version=version)
        preview = self.api.post(self.base + "pages/preview", json=body)
        self.assertEqual(preview.status_code, 200, preview.text)
        body.update(preview=preview.json()["preview"], approved_for_public=True)
        for _ in range(2):
            result = self.api.post(self.base + "pages/draft-pr", json=body)
            self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(sum(k == "/pulls" for k, d in self.posts), 1)
        blobs = [
            base64.b64decode(d["content"]) for k, d in self.posts if k == "/git/blobs"
        ]
        self.assertTrue(any(digest(raw) == mid for raw in blobs))
        self.assertTrue(any(b"Open original screenshot" in raw for raw in blobs))
        self.assertTrue(
            any(self.index[:12] in raw and b"sofa-guide" in raw for raw in blobs)
        )

    def test_provider_response_lost_after_ref_creation_can_recover(self):
        _, version, _ = self.library_save()
        body = dict(path=self.path, version=version)
        preview = self.api.post(self.base + "pages/preview", json=body).json()
        body.update(preview=preview["preview"], approved_for_public=True)

        def timeout_on_ref(config, repo, endpoint, payload):
            result = self.post(config, repo, endpoint, payload)
            if endpoint == "/git/refs":
                raise Rejected("Connection lost after branch creation.")
            return result

        with patch.object(pages, "write", timeout_on_ref):
            self.assertEqual(
                self.api.post(self.base + "pages/draft-pr", json=body).status_code, 409
            )
        self.assertFalse(self.prs)
        self.assertEqual(
            self.api.post(self.base + "pages/draft-pr", json=body).status_code, 200
        )
        self.assertEqual(sum(k == "/git/refs" for k, d in self.posts), 1)
        self.assertEqual(len(self.prs), 1)

    def test_wrong_repository_or_branch_blocks_installation_request(self):
        _, version, _ = self.library_save()
        self.binding.return_value["pages_github_app"]["repository"] = "another/repo"
        response = self.api.post(
            self.base + "pages/preview", json=dict(path=self.path, version=version)
        )
        self.assertEqual(response.status_code, 409)
        self.access.assert_not_called()
        self.assertEqual(self.posts, [])

    def test_denied_and_stale_decisions_make_no_provider_write(self):
        _, version, _ = self.library_save()
        body = dict(path=self.path, version=version)
        url = self.base + "pages/preview"
        self.assertEqual(self.client("editor").post(url, json=body).status_code, 403)
        self.assertEqual(
            self.api.post(url, json={**body, "version": "f" * 64}).status_code, 409
        )
        preview = self.api.post(url, json=body).json()["preview"]
        body.update(preview=preview, approved_for_public=False)
        self.assertEqual(
            self.api.post(self.base + "pages/draft-pr", json=body).status_code, 409
        )
        self.head = "e" * 40
        self.assertEqual(
            self.api.post(
                self.base + "pages/draft-pr", json={**body, "approved_for_public": True}
            ).status_code,
            409,
        )
        self.assertEqual(self.posts, [])


del _GuideFixtures


class DisclosureTests(unittest.TestCase):
    def test_seeded_private_note_or_credential_is_blocked_before_media_is_read(self):
        for value in (
            "Internal-only: draft sales forecast",
            "api_key=synthetic-fixture",
            "<!-- private note -->",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(Rejected, "restricted"),
            ):
                pages.guide_files(
                    "docs/guide.md", "a" * 64, value, [], self.fail, "test"
                )

    def test_changed_capture_is_rejected(self):
        mid = "b" * 64
        media = [{"path": f"evidence/{'a' * 64}/assets/{mid}.png", "digest": mid}]
        with self.assertRaisesRegex(Rejected, "approved bytes"):
            pages.guide_files(
                "docs/guide.md",
                "a" * 64,
                "# Guide",
                media,
                lambda _: b"changed",
                "test",
            )

    def test_public_markup_is_escaped_and_unreviewed_links_are_rejected(self):
        raw = b"synthetic fixture"
        mid = digest(raw)
        ref = f"evidence/{'a' * 64}/assets/{mid}.png"
        media = [{"path": ref, "digest": mid}]
        body = f"# Guide\n\nA literal <mark>example</mark>.\n\n![Inbox](../{ref})"
        files, guide, _ = pages.guide_files(
            "docs/guide.md", "b" * 64, body, media, lambda _: raw, "fixture"
        )
        self.assertIn(b"&lt;mark&gt;", files[guide])
        self.assertNotIn(b"<mark>", files[guide])
        with self.assertRaisesRegex(Rejected, "guide links"):
            pages.guide_files(
                "docs/guide.md",
                "b" * 64,
                body + "\n[Ticket](https://example.org/private)",
                media,
                lambda _: raw,
                "fixture",
            )
