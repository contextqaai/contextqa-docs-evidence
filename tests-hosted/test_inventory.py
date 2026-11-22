import json
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from inventory_fixture import Repository, connect
from psycopg_pool import ConnectionPool

from cqa_artifacts.hosted.auth import Settings
from cqa_artifacts.hosted.server import create_app
from cqa_artifacts.hosted.store import PostgresStore

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class InventoryTests(unittest.TestCase):
    def setUp(self):
        url = os.environ["TEST_DATABASE_URL"]
        self.pool = ConnectionPool(url)
        self.addCleanup(self.pool.close)
        self.org = "inventory-" + uuid.uuid4().hex
        with self.pool.connection() as db:
            for f in sorted((ROOT / "migrations").glob("*.sql")):
                db.execute(f.read_text())
            db.execute(
                "INSERT INTO docs_organizations VALUES(%s,%s)", (self.org, self.org)
            )
            db.execute(
                "INSERT INTO docs_memberships VALUES(%s,'owner','admin'),(%s,'writer','editor')",
                (self.org, self.org),
            )
        self.addCleanup(self.cleanup_org)
        manifest = json.loads((ROOT / "examples/kan-pr15/manifest.json").read_text())
        manifest["project_id"] = "docs"
        self.store = PostgresStore(self.pool, self.org)
        self.store.create(manifest, "owner")
        with self.pool.connection() as db:
            connect(db, self.org, "docs", "example/handbook")
        settings = Settings(
            url,
            "http://127.0.0.1:8080",
            mode="development",
            auth_mode="development",
            dev_token="x" * 40,
            dev_subject="writer",
        )
        self.client = TestClient(
            create_app(settings, self.pool),
            base_url=settings.origin,
            headers={"Authorization": "Bearer " + settings.dev_token},
        )
        self.addCleanup(self.client.close)
        self.url = "/api/orgs/" + self.org + "/projects/docs/inventory"
        self.repo = Repository(invalid=True)
        for target, replacement in [
            ("inventory.binding", lambda *_: {"installation_token": "test"}),
            ("repository_docs.github_get", self.repo.get),
        ]:
            mock = patch("cqa_artifacts.hosted." + target, replacement)
            mock.start()
            self.addCleanup(mock.stop)

    def cleanup_org(self):
        with self.pool.connection() as db:
            db.execute("DELETE FROM docs_organizations WHERE id=%s", (self.org,))

    def post(self, suffix, expected=200):
        res = self.client.post(self.url + "/" + suffix, json={})
        self.assertEqual(res.status_code, expected, res.text)
        return res.json()

    def preview(self):
        j = self.post("preview")
        while j["status"] == "reading":
            j = self.post(j["id"] + "/read")
        return j

    def apply(self):
        return self.post(self.preview()["id"] + "/apply")

    def articles(self):
        return self.store.snapshot("docs", "writer")["articles"]

    def test_versioned_import_figures_and_separate_paths(self):
        preview = self.preview()
        self.assertFalse(self.articles())
        self.assertEqual(sum(f["duplicate_title"] for f in preview["files"]), 2)
        res = self.post(preview["id"] + "/apply")
        self.assertEqual(
            res["summary"], {"created": 2, "updated": 0, "unchanged": 0, "skipped": 2}
        )
        source = self.articles()["teams/setup.mdx"]["imported"]
        self.assertNotEqual(
            source["id"], self.articles()["admin/setup.md"]["imported"]["id"]
        )
        self.assertEqual(
            (source["repo_path"], source["reader_path"], source["navigation"]),
            ("docs/teams/setup.mdx", "/team-onboarding", ["Team guides"]),
        )
        url = self.url + "/figure/" + res["id"]
        self.assertTrue(
            self.client.get(url, params={"path": "images/invitation.png"})
            .json()["src"]
            .startswith("data:image/png;base64,")
        )
        self.assertEqual(
            self.client.get(url, params={"path": "docs.json"}).status_code, 404
        )
        self.assertEqual(self.apply()["summary"]["unchanged"], 2)
        self.repo.files["teams/setup.mdx"] += b"\nA new paragraph.\n"
        self.assertEqual(self.apply()["summary"]["updated"], 1)
        new = self.articles()["teams/setup.mdx"]["imported"]
        self.assertEqual((source["id"], 2), (new["id"], new["version"]))
        with self.pool.connection() as db:
            self.assertEqual(
                db.execute(
                    "SELECT count(*) FROM docs_import_versions WHERE organization_id=%s",
                    (self.org,),
                ).fetchone()[0],
                3,
            )

    def test_partial_listing_missing_files_and_read_retry(self):
        self.apply()
        before = self.articles()
        self.repo.truncate = True
        self.assertIn("incomplete", self.post("preview", 409)["detail"])
        self.assertEqual(self.articles(), before)
        del self.repo.files["teams/setup.mdx"]
        next_job = self.post("preview")["id"]
        self.post(next_job + "/read")
        self.repo.fail_blob = True
        self.post(next_job + "/read", 502)
        saved = self.client.get(self.url).json()
        self.assertEqual(sum(f["status"] == "ready" for f in saved["files"]), 1)
        self.post(next_job + "/apply", 409)
        while saved["status"] == "reading":
            saved = self.post(next_job + "/read")
        self.post(next_job + "/apply")
        self.assertEqual(self.articles(), before)

    def test_newer_job_scope_and_edit_conflicts(self):
        old = self.preview()
        new = self.preview()
        self.post(old["id"] + "/apply", 409)
        self.store.article(
            "docs", "writer", "admin/setup.md", "My title", "# Local baseline"
        )
        self.post(new["id"] + "/apply", 409)
        clean = self.apply()
        self.assertEqual(clean["summary"]["skipped"], 3)
        self.assertEqual(self.articles()["admin/setup.md"]["body"], "# Local baseline")
        pending = self.preview()
        with self.pool.connection() as db:
            db.execute(
                "UPDATE docs_setup SET connected=false WHERE organization_id=%s",
                (self.org,),
            )
        self.post(pending["id"] + "/apply", 409)

    def test_reader_path_collision_and_malformed_navigation_are_file_scoped(self):
        self.repo.files["extra.md"] = (
            b"---\nslug: /team-onboarding\n---\n# Another topic"
        )
        self.repo.files["mint.json"] = (
            b'{"navigation":[{"group":"bad\\u0000","pages":["extra"]}]}'
        )
        job = self.preview()
        self.assertTrue(
            any(
                "Shared reader path /team-onboarding" in warning
                for warning in job["warnings"]
            )
        )
        self.assertEqual(
            next(f for f in job["files"] if f["path"] == "mint.json")["status"],
            "skipped",
        )
        self.assertEqual(self.post(job["id"] + "/apply")["summary"]["created"], 3)

    def test_import_and_artifact_access_require_current_role(self):
        job = self.apply()["id"]
        with self.pool.connection() as db:
            db.execute(
                "UPDATE docs_memberships SET role='contributor' WHERE organization_id=%s AND subject='writer'",
                (self.org,),
            )
        self.post("preview", 403)
        self.post(job + "/apply", 403)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(
            self.client.get(
                self.url + "/figure/" + job, params={"path": "images/invitation.png"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(self.url.replace(self.org, "other-company")).status_code,
            404,
        )
