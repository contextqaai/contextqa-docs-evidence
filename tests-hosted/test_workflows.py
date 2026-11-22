import json
import os
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from cqa_artifacts.hosted.auth import Settings
from cqa_artifacts.hosted.server import create_app
from cqa_artifacts.hosted.store import PostgresStore
from cqa_artifacts.hosted.workflow_worker import checkpoint, claim, dispatch, tick
from cqa_artifacts.hosted.workflows import scheduled_instant

ROOT = Path(__file__).resolve().parents[1]


class ScheduleTests(unittest.TestCase):
    def test_skipped_and_repeated_times(self):
        self.assertEqual(
            scheduled_instant(date(2026, 3, 8), "02:30", "America/Chicago"),
            datetime(2026, 3, 8, 8, tzinfo=timezone.utc),
        )
        self.assertEqual(
            scheduled_instant(date(2026, 11, 1), "01:30", "America/Chicago"),
            datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc),
        )


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.org = "workflow-" + uuid.uuid4().hex
        url = os.environ["TEST_DATABASE_URL"]
        self.pool = ConnectionPool(url)
        self.addCleanup(self.pool.close)
        with self.pool.connection() as db:
            db.execute(
                "INSERT INTO docs_organizations(id,name) VALUES(%s,%s)",
                (self.org, self.org),
            )
            db.execute(
                "INSERT INTO docs_memberships VALUES(%s,'owner','admin')", (self.org,)
            )
        self.addCleanup(self.cleanup_org)
        manifest = json.loads((ROOT / "examples/kan-pr15/manifest.json").read_text())
        manifest["project_id"] = "docs"
        self.store = PostgresStore(self.pool, self.org)
        self.store.create(manifest, "owner")
        settings = Settings(
            url,
            "http://127.0.0.1:8080",
            mode="development",
            auth_mode="development",
            dev_token="x" * 40,
            dev_subject="owner",
        )
        self.client = TestClient(
            create_app(settings, self.pool),
            base_url=settings.origin,
            headers={"Authorization": "Bearer " + settings.dev_token},
        )
        self.addCleanup(self.client.close)
        self.url = "/api/orgs/" + self.org + "/projects/docs/workflow"
        self.spec = {
            "version": 0,
            "instructions": "Review the inventory.",
            "page_limit": 5,
            "trigger": "github",
            "timezone": "UTC",
            "local_time": "09:00",
        }

    def cleanup_org(self):
        with self.pool.connection() as db:
            db.execute("DELETE FROM docs_organizations WHERE id=%s", (self.org,))

    def post(self, action, data, code=200):
        r = self.client.post(self.url + "/" + action, json=data)
        self.assertEqual(r.status_code, code, r.text)
        return r.json()

    def test_lease_recovery_pinned_version_and_test_cursor(self):
        self.post("save", self.spec)
        key = str(uuid.uuid4())
        job = self.post("test", {"version": 1, "request_id": key})["id"]
        self.assertEqual(
            self.post("test", {"version": 1, "request_id": key})["id"], job
        )
        self.post("test", {"version": 1, "request_id": str(uuid.uuid4())}, 409)
        abandoned = claim(self.pool)
        with self.pool.connection() as db:
            db.execute(
                "UPDATE docs_runs SET expires_at=now()-interval '1 second' WHERE id=%s",
                (job,),
            )
        reclaimed = claim(self.pool)
        self.assertFalse(checkpoint(self.pool, *abandoned))
        self.assertTrue(checkpoint(self.pool, *reclaimed))
        self.post(
            "save", {**self.spec, "version": 1, "instructions": "New instructions."}
        )
        self.assertTrue(tick(self.pool))
        run = self.client.get(self.url + "/runs/" + job).json()
        self.assertEqual(run["status"], "needs_input")
        self.store.article("docs", "owner", "start.md", "Start", "# Start")
        self.post("runs/" + job + "/resume", {})
        while tick(self.pool):
            pass
        run = self.client.get(self.url + "/runs/" + job).json()
        self.assertEqual([r["stage"] for r in run["receipts"]], [0, 1, 2])
        self.assertEqual(run["config"]["instructions"], self.spec["instructions"])
        self.assertEqual(run["status"], "succeeded")
        self.assertIsNone(self.client.get(self.url).json()["workflow"]["live_cursor"])

    def test_invalid_schedule_source_and_daily_backlog(self):
        self.post("save", {**self.spec, "timezone": "no/suchzone"}, 422)
        self.post("save", self.spec)
        self.post("activate", {"version": 1, "backlog": "skip"}, 409)
        self.post("save", {**self.spec, "version": 1, "trigger": "daily"})
        self.post("activate", {"version": 2, "backlog": "process"})
        dispatch(self.pool)
        dispatch(self.pool)
        data = self.client.get(self.url).json()
        self.assertEqual(len(data["runs"]), 1)
        self.assertEqual(data["runs"][0]["mode"], "daily")
        self.post("pause", {"version": 2})
        self.assertIsNone(claim(self.pool))

    def test_github_skip_resume_dedup_and_budget(self):
        self.post("save", {**self.spec, "page_limit": 1})
        with self.pool.connection() as db:
            db.execute(
                "INSERT INTO docs_setup(organization_id,project_id,connected,product_repo) VALUES(%s,'docs',true,'acme/product')",
                (self.org,),
            )

        def source(key):
            item = self.store.ingest(
                "docs",
                "owner",
                {
                    "id": key,
                    "source": "github",
                    "title": "Review changes",
                    "text": "Check detail.",
                },
            )["item_id"]
            with self.pool.connection() as db:
                db.execute(
                    """INSERT INTO docs_source_deliveries(organization_id,project_id,delivery,payload_hash,repository,revision,item_id)
                     VALUES(%s,'docs',%s,%s,'acme/product',%s,%s)""",
                    (self.org, key, key, key, item),
                )

        source("old")
        self.post("activate", {"version": 1, "backlog": "skip"})
        dispatch(self.pool)
        self.assertEqual(
            self.client.get(self.url).json()["runs"][0]["status"], "skipped"
        )
        source("new")
        self.store.article("docs", "owner", "a.md", "A", "# A")
        self.store.article("docs", "owner", "b.md", "B", "# B")
        while tick(self.pool):
            pass
        result = self.client.get(self.url).json()
        self.assertEqual(len(result["runs"]), 2)
        self.assertIn("page limit", result["runs"][0]["reason"])
        self.assertEqual(result["workflow"]["live_cursor"], "acme/product@new")
