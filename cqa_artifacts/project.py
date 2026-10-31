"""Read-only reusable ContextQA configuration checks; never create local runners."""
import hashlib
import json
import copy
from . import core
from .contextqa import positive_id, validate


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_project(profile):
    if not isinstance(profile, dict) or profile.get("schema") != 1 or type(profile.get("schema")) is not int:
        raise core.Rejected("Project needs schema 1")
    if set(profile) - {"schema", "name", "plan", "cases", "suites", "steps", "execution"}:
        raise core.Rejected("Unknown project configuration property")
    if not isinstance(profile.get("name"), str) or not profile["name"].strip() or len(profile["name"]) > 120:
        raise core.Rejected("Project needs a name")
    rows = [profile.get("plan")]
    for kind in ("cases", "suites", "steps"):
        selected = profile.get(kind, [])
        if not isinstance(selected, list) or len(selected) > 100:
            raise core.Rejected("Project resource selection exceeds bounds")
        ids = []
        for row in selected:
            if not isinstance(row, dict):
                raise core.Rejected("Invalid project resource")
            ids.append(positive_id(row.get("id")))
        if len(set(ids)) != len(ids):
            raise core.Rejected("Project resource IDs must be unique")
        rows.extend(selected)
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "expect"}:
            raise core.Rejected("Project resources need id and expect")
        positive_id(row["id"])
        if not isinstance(row["expect"], dict) or not row["expect"]:
            raise core.Rejected("Explicit expected ContextQA configuration is required")
        validate(row["expect"], {})
    execution = profile.get("execution", {})
    if not isinstance(execution, dict) or set(execution) - {"query", "maxPolls", "intervalMs"}:
        raise core.Rejected("Unknown project execution option")
    query = execution.get("query", {})
    if not isinstance(query, dict) or set(query) - {"environment"}:
        raise core.Rejected("Docs Evidence saved-plan profiles support only an explicit environment query override")
    if "environment" in query and (not isinstance(query["environment"], str) or len(query["environment"]) > 500 or any(c in query["environment"] for c in "\r\n\0")):
        raise core.Rejected("Invalid project environment override")
    for key, low, high in (("maxPolls", 1, 100), ("intervalMs", 0, 30000)):
        if key in execution and (type(execution[key]) is not int or not low <= execution[key] <= high):
            raise core.Rejected("Project polling option exceeds bounds")
    return profile


def matches(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and matches(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(matches(a, b) for a, b in zip(expected, actual))
    return type(expected) is type(actual) and expected == actual


def inspect_project(client, profile):
    profile = copy.deepcopy(profile)
    validate_project(profile)
    plan = client.call("getTestPlan", id=profile["plan"]["id"])
    if not isinstance(plan, dict) or type(plan.get("id")) is not int or plan.get("id") != profile["plan"]["id"] or not matches(profile["plan"]["expect"], plan):
        raise core.Rejected("ContextQA plan configuration drift; review before execution")
    observed = {"plan": plan, "cases": [], "suites": [], "steps": []}
    for kind, operation in (("cases", "getTestCase"), ("suites", "getTestSuite"), ("steps", "getTestStep")):
        for row in profile.get(kind, []):
            actual = client.call(operation, id=row["id"])
            if not isinstance(actual, dict) or type(actual.get("id")) is not int or actual.get("id") != row["id"] or not matches(row["expect"], actual):
                raise core.Rejected("ContextQA resource configuration drift; review before execution")
            observed[kind].append(actual)
    return {"schema": 1, "projectName": profile["name"], "planId": profile["plan"]["id"], "checked": True,
            "profileSha256": fingerprint(profile), "observedSha256": fingerprint(observed), "observed": observed,
            "paidExecutionStarted": False}
