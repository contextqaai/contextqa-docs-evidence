import copy
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.parse

from cqa_artifacts import core
from cqa_artifacts import contextqa as api


PASS = {"status": "STATUS_COMPLETED", "result": "SUCCESS", "totalCount": 2,
        "passedCount": 2, "failedCount": 0, "abortedCount": 0, "stoppedCount": 0, "notExecutedCount": 0}


class ContextQAContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calls = []

    def client(self, response=None):
        def transport(request, timeout, limit):
            self.calls.append(request)
            return json.dumps(response if response is not None else {"id": 17}).encode()
        return api.ContextQAClient("token_demo.synthetic", transport=transport, simulated=True)

    def test_all_catalog_operations_are_fixed_origin_and_execution_is_not_generic(self):
        self.assertEqual(len(api.OPERATIONS), 26)
        for name, op in api.OPERATIONS.items():
            client = self.client()
            client.call(name, id=17 if "{id}" in op["path"] else None,
                        body={} if op["body"] else None, approve_write=True)
            self.assertEqual(urllib.parse.urlsplit(self.calls[-1].full_url).netloc, "server.contextqa.com")
        for name in ("triggerRun", "triggerRunWithAppFile", "deleteTestCase", "https://attacker.example/"):
            with self.assertRaises(core.Rejected):
                self.client().call(name)

    def test_token_and_authoring_consent_fail_before_transport(self):
        for value in (None, "", "Bearer secret", "token_demo.bad\nheader"):
            with self.assertRaises(core.Rejected):
                api.ContextQAClient(value)
        with self.assertRaises(core.Rejected):
            self.client().call("createTestCase", body={"name": "demo"})
        self.assertEqual(self.calls, [])

    def test_schema_rejects_unknown_nested_fields_wrong_types_and_enums(self):
        invalid = [("createTestCase", {"unknown": True}), ("createTestCase", {"workspaceVersionId": True}),
                   ("createTestCase", {"testType": "MAGIC"}), ("createTestPlan", {"testDevices": [{"unsafe": True}]})]
        for operation, body in invalid:
            with self.subTest(body=body), self.assertRaises(core.Rejected):
                self.client().call(operation, body=body, approve_write=True)
        self.assertEqual(self.calls, [])

    def test_lists_force_bounded_page_and_reject_unrecognized_query(self):
        self.client().call("listTestSteps")
        params = urllib.parse.parse_qs(urllib.parse.urlsplit(self.calls[-1].full_url).query)
        self.assertEqual(params, {"size": ["50"], "page": ["0"]})
        for query in ({"size": 0}, {"size": 101}, {"page": -1}, {"token": "secret"}):
            with self.assertRaises(core.Rejected):
                self.client().call("listTestSteps", query=query)

    def test_transport_errors_are_suppressed_without_retry(self):
        transport = Mock(side_effect=urllib.error.URLError("PRIVATE_TOKEN_AND_UPSTREAM_BODY"))
        client = api.ContextQAClient("token_demo.synthetic", transport=transport)
        with self.assertRaises(core.Rejected) as error:
            client.call("getTestPlan", id=1)
        self.assertNotIn("PRIVATE", str(error.exception))
        self.assertEqual(transport.call_count, 1)
        with patch("urllib.request.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b"{}"
            api.ContextQAClient._http(urllib.request.Request(core.API), 1, 10)
            self.assertIsInstance(opener.call_args.args[-1], core.NoRedirect)

    def test_oversized_response_is_rejected(self):
        client = api.ContextQAClient("token_demo.synthetic", transport=lambda *args: b"x" * (core.MAX_JSON + 1))
        with self.assertRaises(core.Rejected):
            client.call("getTestPlan", id=1)

    def test_response_output_is_reserved_before_remote_authoring(self):
        destination = self.root / "response.json"
        def transport(request, timeout, limit):
            self.assertEqual(json.loads(destination.read_text())["state"], "intent")
            with self.assertRaises(FileExistsError):
                self.client().call_to_file("createTestCase", destination, body={}, approve_write=True)
            self.calls.append(request)
            return b'{"id":17}'
        client = api.ContextQAClient("token_demo.synthetic", transport=transport, simulated=True)
        client.call_to_file("createTestCase", destination, body={}, approve_write=True)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(json.loads(destination.read_text()), {"id": 17})
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)

    def test_failed_authoring_leaves_reserved_failure_receipt(self):
        destination = self.root / "response.json"
        transport = Mock(side_effect=TimeoutError())
        client = api.ContextQAClient("token_demo.synthetic", transport=transport)
        with self.assertRaises(core.Rejected):
            client.call_to_file("createTestCase", destination, body={}, approve_write=True)
        self.assertEqual(json.loads(destination.read_text())["state"], "failed_or_ambiguous")
        with self.assertRaises(FileExistsError):
            client.call_to_file("createTestCase", destination, body={}, approve_write=True)
        self.assertEqual(transport.call_count, 1)

    def test_real_client_spaces_requests_and_simulated_mode_needs_transport(self):
        with self.assertRaises(core.Rejected):
            api.ContextQAClient("token_demo.synthetic", simulated=True)
        client = api.ContextQAClient("token_demo.synthetic", transport=lambda *args: b"{}")
        with patch.object(api.time, "monotonic", side_effect=[10, 10.1, 10.55]), patch.object(api.time, "sleep") as sleep:
            client.call("getTestPlan", id=1)
            client.call("getTestPlan", id=1)
            self.assertAlmostEqual(sleep.call_args.args[0], 0.45)

    def test_selected_run_snapshot_contradiction_never_passes(self):
        data = {"summary": PASS, "cases": [], "steps": [], "suites": [], "run_record": dict(PASS, result="FAILURE")}
        self.assertEqual(api.selected_assessment(data), "inconclusive")
        data["run_record"] = None
        data["steps"] = [{"result": "FAILURE"}]
        self.assertEqual(api.selected_assessment(data), "failed")

    def test_cli_run_profile_is_checked_before_start_and_rejects_environment_drift(self):
        from cqa_artifacts.__main__ import main
        profile = self.root / "profile.json"
        profile.write_text(json.dumps({"plan": {"id": 7}, "execution": {"query": {"environment": "staging"}}}))
        args = ["cqa-artifacts", "contextqa-run", "--plan-id", "7", "--journal", str(self.root / "run.jsonl"), "--profile", str(profile), "--approve-execution"]
        checked = {"checked": True, "planId": 7, "profileSha256": "a" * 64, "observedSha256": "b" * 64}
        client = Mock()
        client.trigger_run.return_value = {"state": "accepted", "run_id": 91}
        with patch("sys.argv", args), patch.dict("os.environ", {"CONTEXTQA_API_TOKEN": "token_demo.synthetic"}), patch.object(api, "ContextQAClient", return_value=client), patch("cqa_artifacts.project.inspect_project", return_value=checked) as inspect, contextlib.redirect_stdout(io.StringIO()):
            main()
            inspect.assert_called_once()
            self.assertEqual(client.trigger_run.call_args.kwargs["environment"], "staging")
            self.assertEqual(client.trigger_run.call_args.kwargs["preflight"], checked)
        client.reset_mock()
        with patch("sys.argv", args + ["--environment", "production"]), patch.dict("os.environ", {"CONTEXTQA_API_TOKEN": "token_demo.synthetic"}), patch.object(api, "ContextQAClient", return_value=client), patch("cqa_artifacts.project.inspect_project") as inspect:
            with self.assertRaises(core.Rejected):
                main()
            inspect.assert_not_called()
            client.trigger_run.assert_not_called()

    def test_cli_project_check_preserves_readonly_verified_receipt(self):
        from cqa_artifacts.__main__ import main
        profile = self.root / "profile.json"
        profile.write_text("{}")
        output = self.root / "checked.json"
        checked = {"checked": True, "planId": 7, "profileSha256": "a" * 64, "observedSha256": "b" * 64, "paidExecutionStarted": False}
        def inspect(client, data):
            self.assertEqual(json.loads(output.read_text())["state"], "project_check_intent")
            return checked
        args = ["cqa-artifacts", "contextqa-project-check", "--profile", str(profile), "--out", str(output)]
        with patch("sys.argv", args), patch.dict("os.environ", {"CONTEXTQA_API_TOKEN": "token_demo.synthetic"}), patch.object(api, "ContextQAClient"), patch("cqa_artifacts.project.inspect_project", side_effect=inspect), contextlib.redirect_stdout(io.StringIO()):
            main()
        self.assertEqual(json.loads(output.read_text()), checked)

    def test_journal_intent_is_durable_before_single_start_and_blocks_reuse(self):
        journal = self.root / "private" / "run.jsonl"
        def transport(request, timeout, limit):
            events = [json.loads(line) for line in journal.read_text().splitlines()]
            self.assertEqual(events[0]["state"], "intent")
            self.assertNotIn("token_demo", journal.read_text())
            self.calls.append(request)
            return b'{"id":91}'
        client = api.ContextQAClient("token_demo.synthetic", transport=transport)
        with self.assertRaises(core.Rejected):
            client.trigger_run(7, journal)
        self.assertFalse(journal.exists())
        client.trigger_run(7, journal, approve_execution=True)
        self.assertEqual(api.recorded_run(journal), 91)
        self.assertEqual(stat.S_IMODE(journal.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            client.trigger_run(7, journal, approve_execution=True)
        self.assertEqual(len(self.calls), 1)

    def test_ambiguous_start_stays_journalled_and_never_retries(self):
        journal = self.root / "run.jsonl"
        transport = Mock(side_effect=TimeoutError())
        client = api.ContextQAClient("token_demo.synthetic", transport=transport)
        with self.assertRaises(core.Rejected):
            client.trigger_run(7, journal, approve_execution=True)
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(json.loads(journal.read_text().splitlines()[-1])["state"], "ambiguous")
        with self.assertRaises(core.Rejected):
            api.recorded_run(journal)

    def test_pass_requires_terminal_success_and_positive_consistent_complete_counts(self):
        self.assertEqual(api.assessment(PASS), "passed")
        for change in ({"status": "STATUS_IN_PROGRESS"}, {"totalCount": 0}, {"passedCount": True},
                       {"failedCount": 1}, {"notExecutedCount": None}, {"result": "SKIPPED"}, {"queuedCount": 1}):
            self.assertEqual(api.assessment(dict(PASS, **change)), "inconclusive")
        for key in api.COUNT_FIELDS:
            value = dict(PASS)
            value.pop(key)
            self.assertEqual(api.assessment(value), "inconclusive")
        self.assertEqual(api.assessment(dict(PASS, result="FAILURE")), "failed")

    def test_poll_is_bounded_and_never_cancels_or_starts(self):
        client = self.client({"status": "STATUS_IN_PROGRESS", "result": "IN_PROGRESS"})
        result = client.poll_run(91, max_attempts=2, interval=0)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertFalse(result["upstream_cancelled"])
        self.assertTrue(all('/test_plan_results/91/results' in item.full_url for item in self.calls))

    def test_cross_run_case_or_cross_case_step_is_rejected_without_saved_results(self):
        workspace = self.root / "workspace"
        core.init(workspace, "Test")
        for responses in ([PASS, {"id": 2, "testPlanResultId": 999}],
                          [PASS, {"id": 2, "testPlanResultId": 1}, {"id": 3, "testCaseResultId": 999}]):
            client = api.ContextQAClient("token_demo.synthetic", transport=Mock(side_effect=[json.dumps(x).encode() for x in responses]))
            with self.assertRaises(core.Rejected):
                api.collect_results(client, workspace, 1, [2], [3] if len(responses) == 3 else [])
            self.assertFalse((workspace / "private/contextqa-results.json").exists())

    def test_full_known_artifact_reference_fields_stay_private(self):
        record = {field: {"nested": ["https://assets.example/" + field + "?signature=PRIVATE"]} for field in api.ARTIFACT_FIELDS}
        refs = api.artifact_references([("step:1", record)])
        self.assertEqual(len(refs), len(api.ARTIFACT_FIELDS))
        self.assertTrue(all("PRIVATE" in item["url"] for item in refs))
        self.assertEqual(api.artifact_references([("step:1", {"notAnArtifact": "https://secret.example"})]), [])

    def test_simulated_end_to_end_creates_source_linked_guide_without_fabricated_images(self):
        script = Path(__file__).resolve().parents[1] / "examples/contextqa_demo.py"
        spec = importlib.util.spec_from_file_location("contextqa_demo", script)
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        destination = self.root / "demo"
        result = demo.main(destination)
        self.assertEqual(result["live_api_calls"], 0)
        self.assertFalse(result["browser_executed"])
        self.assertEqual(result["collection"]["artifact_references"], 3)
        data = core.load_json(destination / "guide/manifest.json")
        self.assertEqual(data["execution"]["transport"], "simulated")
        self.assertEqual(data["steps"][0]["step_result_id"], 903)
        self.assertEqual(data["media"], [])
        self.assertEqual([p.name for p in (destination / "guide/assets").iterdir()], ["contextqa-logo.svg"])
        for filename in ("guide.md", "index.html", "manifest.json"):
            content = (destination / "guide" / filename).read_text()
            self.assertNotIn("SIMULATED_PRIVATE", content)
            self.assertNotIn("artifacts.example", content)
        self.assertIn("SIMULATED TRANSPORT", (destination / "guide/index.html").read_text())
        raw = core.load_json(destination / "workspace/private/contextqa-results.json")
        self.assertEqual(raw["plan_snapshot"]["parallelNode"], 2)


if __name__ == "__main__":
    unittest.main()
