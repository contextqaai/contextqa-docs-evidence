"""PostgreSQL checks for ambiguous charges, scope and evidence review boundaries."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool
from cqa_artifacts.hosted.auth import Settings
from cqa_artifacts.hosted.server import create_app
from cqa_artifacts.hosted.store import PostgresStore
from cqa_artifacts.hosted.capture_worker import tick


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class CaptureTests(unittest.TestCase):
    def setUp(self):
        url = os.environ["TEST_DATABASE_URL"]
        self.org = "capture-" + uuid4().hex
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
        manifest = json.loads(
            (
                Path(__file__).resolve().parents[1] / "examples/kan-pr15/manifest.json"
            ).read_text()
        )
        manifest["project_id"] = "docs"
        PostgresStore(self.pool, self.org).create(manifest, "owner")
        settings = Settings(
            url,
            "http://127.0.0.1:8080",
            mode="development",
            auth_mode="development",
            dev_token="x" * 40,
            dev_subject="owner",
        )
        self.api = TestClient(
            create_app(settings, self.pool),
            base_url=settings.origin,
            headers={"Authorization": "Bearer " + settings.dev_token},
        )
        self.addCleanup(self.api.close)
        self.base = "/api/orgs/" + self.org + "/projects/docs/captures"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(
            os.environ,
            {"DOCS_CAPTURE_ROOT": self.tmp.name, "DOCS_CONNECTIONS_FILE": ""},
        )
        env.start()
        self.addCleanup(env.stop)

    def cleanup_org(self):
        with self.pool.connection() as db:
            db.execute("DELETE FROM docs_organizations WHERE id=%s", (self.org,))

    def job(self, state):
        ident = uuid4()
        with self.pool.connection() as db:
            db.execute(
                """INSERT INTO docs_capture_jobs(id,organization_id,project_id,request_id,journey,digest,registry,revision,status)
                     VALUES(%s,%s,'docs',%s,'case',%s,'{}',%s,%s)""",
                (ident, self.org, uuid4(), "f" * 64, "a" * 40, state),
            )
        return ident

    def test_missing_binding_and_consent(self):
        result = self.api.get(self.base)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["profiles"], [])
        self.assertEqual(self.api.post(self.base + "/case/register").status_code, 409)
        self.assertEqual(
            self.api.post(
                self.base + "/case/replay",
                json={
                    "revision": "a" * 40,
                    "digest": "f" * 64,
                    "request_id": str(uuid4()),
                    "confirm": False,
                },
            ).status_code,
            422,
        )
        self.assertEqual(
            self.api.get(self.base.replace(self.org, "another-org")).status_code, 404
        )

    def test_unknown_start_is_never_reexecuted(self):
        job = self.job("starting")
        self.assertTrue(tick(self.pool))
        row = self.api.get(self.base).json()["jobs"][0]
        self.assertEqual(row["status"], "reconcile")
        path = self.base + "/jobs/" + str(job) + "/check"
        self.assertEqual(self.api.post(path).status_code, 409)
        self.assertFalse(tick(self.pool))
        directory = Path(self.tmp.name) / str(job)
        directory.mkdir()
        (directory / "start.jsonl").write_text(
            json.dumps({"state": "accepted", "run_id": 55}) + "\n"
        )
        self.assertEqual(self.api.post(path).json()["provider_run"], 55)
        row = self.api.get(self.base).json()["jobs"][0]
        self.assertEqual((row["status"], row["provider_run"]), ("running", 55))

    def test_unverified_media_cannot_be_approved_or_served(self):
        job = self.job("needs_evidence")
        path = self.base + "/jobs/" + str(job)
        self.assertEqual(self.api.get(path + "/media/" + "a" * 64).status_code, 404)
        self.assertEqual(
            self.api.post(
                path + "/review", json={"digest": "f" * 64, "confirm": True}
            ).status_code,
            409,
        )
        self.assertEqual(self.api.post(path + "/check").status_code, 409)
        self.assertEqual(
            self.api.post(path.replace(self.org, "other-org") + "/check").status_code,
            404,
        )

    def test_saved_replay_pins_input_and_blocks_drift_before_charge(self):
        from cqa_artifacts import journeys
        from cqa_artifacts.hosted import captures, capture_worker

        reg_path = Path(self.tmp.name) / "registry.json"
        reg = json.loads(
            (
                Path(__file__).resolve().parents[1] / "examples/kan-pr15/journeys.json"
            ).read_text()
        )
        journey = reg["journeys"][0]
        reg_path.write_text(json.dumps(reg))
        config = {
            "capture_registry_file": str(reg_path),
            "workspace_version_id": 1,
            "app_url": journey["application_url"],
            "capture_plan_ids": [journey["profile"]["plan"]["id"]],
            "capture_api_token": "test",
            "capture_meter_note": "Synthetic transport",
        }
        with self.pool.connection() as db:
            db.execute(
                "INSERT INTO docs_setup(organization_id,project_id,app_url,product_repo) VALUES(%s,'docs',%s,%s) ON CONFLICT(organization_id,project_id) DO UPDATE SET product_repo=excluded.product_repo,app_url=excluded.app_url",
                (self.org, journey["application_url"], reg["repository"]),
            )
        path = self.base + "/" + journey["id"]
        with (
            patch.object(captures, "binding", return_value=config),
            patch.object(
                journeys, "register", side_effect=lambda client, value, ident: value
            ),
            patch.object(captures, "capture_client"),
        ):
            registered = self.api.post(path + "/register")
            self.assertEqual(registered.status_code, 200, registered.text)
            args = {
                "confirm": True,
                "digest": registered.json()["digest"],
                "revision": "1" * 40,
                "request_id": str(uuid4()),
            }
            accepted = self.api.post(path + "/replay", json=args)
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertEqual(
                accepted.json(), self.api.post(path + "/replay", json=args).json()
            )
            self.assertEqual(
                accepted.json(),
                self.api.post(
                    path + "/replay", json={**args, "request_id": str(uuid4())}
                ).json(),
            )
            self.assertEqual(
                self.api.post(
                    path + "/replay", json={**args, "revision": "2" * 40}
                ).status_code,
                409,
            )
            journey["environment"] = "changed"
            reg_path.write_text(json.dumps(reg))
            self.assertTrue(self.api.get(self.base).json()["profiles"][0]["drift"])
            self.assertEqual(
                self.api.post(
                    path + "/replay", json={**args, "request_id": str(uuid4())}
                ).status_code,
                409,
            )
            with patch.object(capture_worker, "capture_client") as provider:
                self.assertTrue(tick(self.pool))
                provider.assert_not_called()
            self.assertEqual(
                self.api.get(self.base).json()["jobs"][0]["status"], "blocked"
            )

    def test_same_replay_becomes_reviewable_after_deployment_is_known(self):
        from cqa_artifacts import journeys, media
        from cqa_artifacts.hosted import captures, capture_worker
        from cqa_artifacts.loop import fingerprint
        from tests.test_journeys import FakeClient, PASS

        class Provider(FakeClient):
            def call(self, operation, **kwargs):
                if operation == "listTestSteps":
                    return {"content": [self.step], "last": True}
                return super().call(operation, **kwargs)

            def poll_run(self, run_id, **kwargs):
                return {"verdict": "passed", "summary": PASS}

        provider = Provider()
        root = Path(self.tmp.name)
        journey = {
            "id": "cards",
            "name": "Create card",
            "sections": ["card"],
            "code_paths": ["card.ts"],
            "application_url": "https://demo.example",
            "environment": "QA",
            "workspace_version_id": 1,
            "case_ids": [10],
            "required_media": ["screenshot", "video"],
            "profile": {
                "schema": 1,
                "name": "Card",
                "plan": {"id": 40, "expect": {"workspaceVersionId": 1}},
                "cases": [{"id": 10, "expect": {"workspaceVersionId": 1}}],
            },
        }
        reg = {"schema": 1, "repository": "example/cards", "journeys": [journey]}
        (root / "registry.json").write_text(json.dumps(reg))
        cfg = {
            "capture_registry_file": str(root / "registry.json"),
            "workspace_version_id": 1,
            "app_url": journey["application_url"],
            "capture_plan_ids": [40],
            "capture_api_token": "test",
            "capture_meter_note": "simulated",
            "capture_storage_hosts": ["media.example"],
            "deployment_receipt_directory": str(root),
        }
        with self.pool.connection() as db:
            db.execute(
                "INSERT INTO docs_setup(organization_id,project_id,app_url,product_repo) VALUES(%s,'docs',%s,%s) ON CONFLICT(organization_id,project_id) DO UPDATE SET app_url=excluded.app_url,product_repo=excluded.product_repo",
                (self.org, journey["application_url"], reg["repository"]),
            )
        fetch = media.fetch_media

        def fixture_media(path, index, kind, host):
            data = (
                b"\x89PNG\r\n\x1a\nfixture"
                if kind == "screenshot"
                else b"\0\0\0\x18ftypmp42fixture"
            )
            return fetch(
                path,
                index,
                kind,
                host,
                transport=lambda *args: data,
                resolver=lambda *a, **k: [
                    (None, None, None, None, ("93.184.216.34", 443))
                ],
            )

        with (
            patch.object(captures, "binding", return_value=cfg),
            patch.object(captures, "capture_client", return_value=provider),
            patch.object(capture_worker, "capture_client", return_value=provider),
            patch.object(media, "fetch_media", side_effect=fixture_media),
        ):
            path = self.base + "/cards"
            result = self.api.post(path + "/register")
            self.assertEqual(result.status_code, 200, result.text)
            args = {
                "confirm": True,
                "digest": result.json()["digest"],
                "revision": "1" * 40,
                "request_id": str(uuid4()),
            }
            accepted = self.api.post(path + "/replay", json=args)
            self.assertEqual(accepted.status_code, 200, accepted.text)
            ident = accepted.json()["id"]
            job_path = self.base + "/jobs/" + ident

            def advance():
                with self.pool.connection() as db:
                    db.execute(
                        "UPDATE docs_capture_jobs SET next_at=now() WHERE id=%s",
                        (ident,),
                    )
                self.assertTrue(tick(self.pool))
                return self.api.get(self.base).json()["jobs"][0]

            self.assertEqual(advance()["status"], "running")
            pending = advance()
            self.assertEqual(pending["status"], "needs_evidence")
            self.assertEqual(pending["receipt"]["requested_deployment"]["run_id"], 30)
            with self.pool.connection() as db:
                locked = db.execute(
                    "SELECT registry FROM docs_capture_jobs WHERE id=%s", (ident,)
                ).fetchone()[0]
            proof = {
                "run_id": 30,
                "commit_sha": args["revision"],
                "application_url": journey["application_url"],
                "environment": "QA",
                "journey_digest": fingerprint(journeys.select(locked, "cards")),
                "verified_by": "Fixture deployer",
                "evidence_ref": "Synthetic deployment",
                "confirmed": True,
            }
            self.assertEqual(
                pending["receipt"]["requested_deployment"],
                {
                    k: proof[k]
                    for k in (
                        "run_id",
                        "commit_sha",
                        "application_url",
                        "environment",
                        "journey_digest",
                    )
                },
            )
            (root / "30.json").write_text(json.dumps(proof))
            self.assertEqual(self.api.post(job_path + "/check").status_code, 200)
            reviewed = advance()
            self.assertEqual(reviewed["status"], "awaiting_review", reviewed)
            item = reviewed["receipt"]["media"][0]
            self.assertEqual(
                self.api.get(job_path + "/media/" + item["id"]).status_code, 200
            )
            self.assertEqual(
                self.api.post(
                    job_path + "/review", json={"digest": "f" * 64, "confirm": True}
                ).status_code,
                409,
            )
            result = self.api.post(
                job_path + "/review",
                json={"digest": reviewed["receipt_digest"], "confirm": True},
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["status"], "reviewed")
            self.assertEqual(provider.started, 1)
