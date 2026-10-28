import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from cqa_artifacts import core
from cqa_artifacts.contextqa import ContextQAClient
from cqa_artifacts.project import inspect_project, validate_project


class ProjectTests(unittest.TestCase):
    def setUp(self):
        sample = Path(__file__).resolve().parents[1] / "examples/contextqa-project.example.json"
        self.profile = json.loads(sample.read_text())

    def client(self, plan=None):
        responses = [dict(self.profile["plan"]["expect"], id=self.profile["plan"]["id"]) if plan is None else plan]
        for kind in ("cases", "suites", "steps"):
            responses.extend(dict(row["expect"], id=row["id"]) for row in self.profile[kind])
        transport = Mock(side_effect=[json.dumps(x).encode() for x in responses])
        return ContextQAClient("token_demo.synthetic", transport=transport, simulated=True), transport

    def test_same_project_verifies_native_environment_data_prerequisites_and_browser_parallel_settings(self):
        client, transport = self.client()
        result = inspect_project(client, self.profile)
        self.assertTrue(result["checked"])
        self.assertFalse(result["paidExecutionStarted"])
        self.assertEqual(result["observed"]["plan"]["testPlanType"], "CROSS_BROWSER")
        self.assertEqual(result["observed"]["cases"][0]["testDataId"], 601)
        self.assertEqual(transport.call_count, 4)
        self.assertTrue(all("/execution" not in call.args[0].full_url for call in transport.call_args_list))

    def test_browser_matrix_drift_stops_before_any_other_call(self):
        plan = dict(self.profile["plan"]["expect"], id=301)
        plan["testDevices"] = plan["testDevices"][:1]
        client, transport = self.client(plan)
        with self.assertRaises(core.Rejected):
            inspect_project(client, self.profile)
        self.assertEqual(transport.call_count, 1)

    def test_missing_data_reference_does_not_satisfy_expected_configuration(self):
        client, transport = self.client()
        expected = copy.deepcopy(self.profile)
        expected["cases"][0]["expect"]["testDataId"] = 999
        with self.assertRaises(core.Rejected):
            inspect_project(client, expected)
        self.assertEqual(transport.call_count, 2)

    def test_unknown_fields_unbounded_polling_and_unsupported_overrides_rejected_offline(self):
        for change in ({"unknown": True}, {"execution": {"maxPolls": 10000}}, {"execution": {"query": {"apk_build_url": "unreviewed"}}}):
            with self.assertRaises(core.Rejected):
                validate_project(dict(self.profile, **change))


if __name__ == "__main__":
    unittest.main()
