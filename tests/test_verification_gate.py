"""Control-plane regressions for release decisions, without executing product tests."""
import runpy
import unittest
from pathlib import Path

gate = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/verification-gate.py"))


class GateTest(unittest.TestCase):
    def setUp(self):
        self.check = dict(id="email", stage="atomic", criterion="Reject empty email",
                          case_id=337, definition="v1")
        self.evidence = dict(spec_revision="v2", build="a", environment=23, definition="v1",
                             case_id=337, result_id=985, result="SUCCESS", assertion_steps=[4],
                             observed_outcome="matches criterion")
        self.record = dict(feature="Email", spec_revision="v2", build="a", environment=23,
                           phases={p: {"checks": ["email"]} for p in gate["PHASES"]},
                           checks=[self.check], guide_disposition="updated",
                           stage_exceptions={s: "Scoped control fixture" for s in gate["STAGES"][1:]})

    def action(self):
        return gate["decision"](self.record)[0]

    def test_reconcile_before_relaunch(self):
        self.check["pending_run"] = {"id": 254}
        self.assertEqual(self.action(), "RECONCILE")

    def test_stale_and_incomplete_evidence(self):
        self.check["evidence"] = self.evidence
        self.assertEqual(self.action(), "READY_FOR_RELEASE_REVIEW")
        self.evidence["build"] = "old"
        self.assertEqual(self.action(), "RUN")
        self.evidence["build"] = "a"
        self.evidence["assertion_steps"] = []
        self.assertEqual(self.action(), "REVIEW_EVIDENCE")

    def test_failure_and_repair(self):
        self.check["evidence"] = dict(self.evidence, result="FAILURE")
        self.assertEqual(self.action(), "DIAGNOSE")
        self.check["repair"] = {"for_result": 985, "change": "Restore the fixture"}
        self.assertEqual(self.action(), "REPLAY")

    def test_missing_phase_and_stage(self):
        self.record["phases"].pop("database")
        self.assertEqual(self.action(), "PLAN")
        self.record["phases"]["database"] = {"inapplicable_reason": "Browser-only fixture"}
        self.check["evidence"] = self.evidence
        self.record["stage_exceptions"].pop("deployed")
        self.assertEqual(self.action(), "PLAN")
