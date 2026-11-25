"""Read a feature's ContextQA verification ledger and identify its next action."""
import argparse
import json
from pathlib import Path

PHASES = (
    "functional", "api", "database", "compatibility", "performance", "security",
    "accessibility", "negative", "edge", "integration", "application_security",
)
STAGES = ("atomic", "contract", "journey", "specialist", "pr_impact", "deployed")


def decision(record):
    """Use reconciled evidence. This command does not launch or charge for runs."""
    for key in ("feature", "spec_revision", "build", "environment"):
        if not record.get(key):
            return "PLAN", f"Record {key}"
    checks = record.get("checks", [])
    ids = [c["id"] for c in checks]
    if not ids or len(ids) != len(set(ids)):
        return "PLAN", "Supply a nonempty list of unique acceptance checks"
    if any(c.get("stage") not in STAGES or not c.get("criterion") for c in checks):
        return "PLAN", "Each check needs a named stage and criterion"
    phases = record.get("phases", {})
    for phase in PHASES:
        coverage = phases.get(phase, {})
        assigned = coverage.get("checks", [])
        if assigned and set(assigned) <= set(ids) and not coverage.get("inapplicable_reason"):
            continue
        if not assigned and isinstance(coverage.get("inapplicable_reason"), str) and coverage["inapplicable_reason"].strip():
            continue
        return "PLAN", f"Map {phase} to checks or record why it does not apply"
    for stage in STAGES:
        rows = [c for c in checks if c["stage"] == stage]
        if not rows and not record.get("stage_exceptions", {}).get(stage, "").strip():
            return "PLAN", f"Supply checks or an explicit scope decision for {stage}"
        for check in rows:
            label = f"{stage} / {check['id']}"
            # An unresolved launch stays pending even when a new build arrives.
            if check.get("pending_run"):
                return "RECONCILE", label
            target = check.get("environment", record["environment"])
            expected = (record["spec_revision"], record["build"], target, check.get("definition"))
            evidence = check.get("evidence", {})
            observed = tuple(evidence.get(k) for k in ("spec_revision", "build", "environment", "definition"))
            if not expected[-1] or not check.get("case_id"):
                return "AUTHOR", label
            if expected != observed or check["case_id"] != evidence.get("case_id"):
                return "RUN", label
            if evidence.get("result") != "SUCCESS":
                repair = check.get("repair", {})
                if evidence.get("result_id") and repair.get("for_result") == evidence["result_id"] and repair.get("change"):
                    return "REPLAY", label
                return "DIAGNOSE", label
            if not evidence.get("result_id") or not evidence.get("assertion_steps"):
                return "REVIEW_EVIDENCE", label
            if evidence.get("observed_outcome") != "matches criterion":
                return "REVIEW_EVIDENCE", label
    if record.get("guide_disposition") not in ("created", "updated", "retired", "no change"):
        return "REVIEW_GUIDE", record["feature"]
    return "READY_FOR_RELEASE_REVIEW", record["feature"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    try:
        action, subject = decision(json.loads(args.ledger.read_text()))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(2, f"NO-GO: invalid verification ledger ({error})\n")
    print(json.dumps({"action": action, "subject": subject, "disposition":
          "READY_FOR_REVIEW" if action == "READY_FOR_RELEASE_REVIEW" else "NO-GO"}))
    raise SystemExit(0 if action == "READY_FOR_RELEASE_REVIEW" else 1)
