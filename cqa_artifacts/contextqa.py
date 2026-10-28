"""ContextQA token API: bounded JSON operations and explicit saved-plan runs.

The injected transport is for tests; ordinary calls use one fixed HTTPS origin.
No artifact URL is fetched and no operation is retried automatically.
"""
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

from . import core

CONTRACT = json.loads(Path(__file__).with_name("contextqa-contract.json").read_text())
OPERATIONS = CONTRACT["operations"]
COUNT_FIELDS = ("passedCount", "failedCount", "abortedCount", "stoppedCount", "notExecutedCount")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def positive_id(value):
    if type(value) is not int or value < 1:
        raise core.Rejected("IDs must be positive integers")
    return value


def validate(value, schema, depth=0):
    if depth > 20:
        raise core.Rejected("JSON exceeds nesting limit")
    if "$ref" in schema:
        return validate(value, CONTRACT["schemas"][schema["$ref"].split("/")[-1]], depth + 1)
    if value is None and schema.get("nullable"):
        return
    kind = schema.get("type")
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "integer": type(value) is int, "number": type(value) in (int, float) and math.isfinite(value),
             "boolean": type(value) is bool, "string": isinstance(value, str)}
    if kind in valid and not valid[kind]:
        raise core.Rejected("JSON value does not match the documented type")
    if "enum" in schema and value not in schema["enum"]:
        raise core.Rejected("JSON value is outside the documented enum")
    if isinstance(value, dict):
        if len(value) > 500:
            raise core.Rejected("JSON object exceeds policy limit")
        props = schema.get("properties", {})
        if props and any(k not in props for k in value):
            raise core.Rejected("Unknown documented DTO field")
        if any(k not in value for k in schema.get("required", [])):
            raise core.Rejected("Missing documented DTO field")
        for key, item in value.items():
            additional = schema.get("additionalProperties", {})
            validate(item, props.get(key, additional if isinstance(additional, dict) else {}), depth + 1)
    elif isinstance(value, list):
        if len(value) > 500:
            raise core.Rejected("JSON array exceeds policy limit")
        for item in value:
            validate(item, schema.get("items", {}), depth + 1)
    elif isinstance(value, str) and len(value) > 128 * 1024:
        raise core.Rejected("JSON string exceeds policy limit")


def exclusive_json(path, data):
    path = Path(path)
    core.private_dir(path.parent)
    with open(path, "x", encoding="utf8", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def replace_private_json(path, data):
    temporary = Path(path).with_name(Path(path).name + "." + uuid.uuid4().hex + ".tmp")
    try:
        exclusive_json(temporary, data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def journal_event(path, event, first=False):
    path = Path(path)
    core.private_dir(path.parent)
    if not first and (path.is_symlink() or not path.is_file() or path.stat().st_size > core.MAX_JSON):
        raise core.Rejected("Invalid run journal")
    flags = os.O_WRONLY | (os.O_CREAT | os.O_EXCL if first else os.O_APPEND)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "a", encoding="utf8") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise core.Rejected("Journal must be a regular file")
        os.chmod(path, 0o600)
        stream.write(json.dumps(dict(event, at=now()), allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if first:
        # Persist the directory entry before any potentially billed request.
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def recorded_run(path):
    raw = core.regular_file(Path(path), core.MAX_JSON)
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    runs = [positive_id(item.get("run_id")) for item in events if item.get("state") == "accepted"]
    if len(runs) != 1:
        raise core.Rejected("Journal has no unique accepted run; reconcile in ContextQA before any new start")
    return runs[0]


def assessment(summary):
    """A completed sequence or zero/missing counts never becomes pass."""
    total = summary.get("totalCount")
    counts = [summary.get(k) for k in COUNT_FIELDS]
    valid = type(total) is int and total > 0 and all(type(n) is int and n >= 0 for n in counts)
    queued = summary.get("queuedCount", 0)
    valid = valid and sum(counts) == total and type(queued) is int and queued == 0
    if summary.get("status") == "STATUS_COMPLETED" and summary.get("result") in {"FAILURE", "ABORTED", "STOPPED"}:
        return "failed"
    passed = valid and summary.get("status") == "STATUS_COMPLETED" and summary.get("result") == "SUCCESS"
    passed = passed and counts[0] == total and all(n == 0 for n in counts[1:])
    return "passed" if passed else "inconclusive"


def selected_assessment(data):
    verdict = assessment(data["summary"])
    run = data.get("run_record")
    if isinstance(run, dict) and any(run.get(key) is not None and data["summary"].get(key) is not None and run[key] != data["summary"][key]
                                     for key in ("status", "result", "totalCount", *COUNT_FIELDS)):
        return "inconclusive"
    selected = data["cases"] + data["steps"] + data["suites"]
    if verdict == "failed" or any(item.get("result") in {"FAILURE", "ABORTED", "STOPPED"} for item in selected):
        return "failed"
    if verdict != "passed" or any(item.get("result") != "SUCCESS" for item in selected):
        return "inconclusive"
    if any(item.get("status") != "STATUS_COMPLETED" for item in data["cases"] + data["suites"]):
        return "inconclusive"
    return "passed"


class ContextQAClient:
    def __init__(self, token, *, transport=None, simulated=False):
        if not isinstance(token, str) or not re.fullmatch(r"token_[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
            raise core.Rejected("Set a valid ContextQA token in CONTEXTQA_API_TOKEN; never a command argument")
        if simulated and transport is None:
            raise core.Rejected("Simulated mode requires an injected test transport")
        self._token = token
        self._transport = transport or self._http
        self.transport_label = "simulated" if simulated else "ContextQA API"
        self._minimum_interval = 0 if simulated else 0.55
        self._last_request = None

    @staticmethod
    def _http(request, timeout, limit):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), core.NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise core.Rejected("ContextQA returned a non-success HTTP status")
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise core.Rejected("ContextQA response exceeds size limit")
            return raw

    def _send(self, method, path, query=None, body=None, timeout=20):
        if not 0 < timeout <= 20:
            raise core.Rejected("Request timeout must be positive and at most 20 seconds")
        encoded = json.dumps(body, allow_nan=False).encode() if body is not None else None
        if encoded is not None and len(encoded) > core.MAX_JSON:
            raise core.Rejected("Request body exceeds size limit")
        url = core.API + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        headers = {"Authorization": "Bearer " + self._token, "Accept": "application/json"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=encoded, headers=headers, method=method)
        try:
            if self._last_request is not None:
                time.sleep(max(0, self._minimum_interval - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            raw = self._transport(request, timeout, core.MAX_JSON)
            if not isinstance(raw, bytes) or len(raw) > core.MAX_JSON:
                raise core.Rejected("Invalid or oversized ContextQA response")
            result = json.loads(raw) if raw.strip() else None
            if result is not None and not isinstance(result, (dict, list)):
                raise core.Rejected("Unexpected ContextQA response type")
            return result
        except urllib.error.HTTPError as error:
            retry = error.headers.get("Retry-After") if error.headers else None
            suffix = "; respect Retry-After before a separately approved safe read" if error.code == 429 and retry else ""
            raise core.Rejected(f"ContextQA request refused (HTTP {error.code}){suffix}; no retry attempted") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            if isinstance(error, core.Rejected):
                raise
            raise core.Rejected("ContextQA request failed; no retry attempted; upstream acceptance may be unknown") from None

    def call(self, operation, *, id=None, query=None, body=None, approve_write=False, timeout=20):
        if operation not in OPERATIONS:
            raise core.Rejected("Unsupported ContextQA operation; arbitrary endpoints and execution are not generic calls")
        op = OPERATIONS[operation]
        path = op["path"]
        if "{id}" in path:
            path = path.replace("{id}", str(positive_id(id)))
        elif id is not None:
            raise core.Rejected("This operation does not accept an ID")
        values = dict(query or {})
        allowed = {p["name"]: p["schema"] for p in op["query"]}
        if any(k not in allowed for k in values):
            raise core.Rejected("Unsupported query parameter")
        if "size" in allowed:
            values.setdefault("size", 50)
            values.setdefault("page", 0)
        for key, value in values.items():
            if key == "sort":
                if not isinstance(value, (str, list)):
                    raise core.Rejected("Sort must be a string or list of strings")
                if isinstance(value, list) and (len(value) > 5 or not all(isinstance(v, str) for v in value)):
                    raise core.Rejected("Sort exceeds policy limit")
            else:
                validate(value, allowed[key])
            if key == "size" and not 1 <= value <= 100 or key == "page" and not 0 <= value <= 10000:
                raise core.Rejected("Pagination exceeds local bounds")
            if isinstance(value, str) and len(value) > 2000:
                raise core.Rejected("Query exceeds local bounds")
            if isinstance(value, bool):
                values[key] = str(value).lower()
        if op["method"] != "GET":
            if not approve_write or not isinstance(body, dict):
                raise core.Rejected("Authoring requires an explicit reviewed JSON body and --approve-write")
            validate(body, op["body"])
        elif body is not None:
            raise core.Rejected("Read operations do not accept a body")
        return self._send(op["method"], path, values, body, timeout)

    def call_to_file(self, operation, destination, **options):
        """Reserve a durable exclusive receipt before any remote authoring."""
        destination = Path(destination)
        exclusive_json(destination, {"operation": operation, "state": "intent", "at": now()})
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        try:
            result = self.call(operation, **options)
            replace_private_json(destination, result)
            return {"saved_privately": True, "operation": operation, "automatic_retry": False}
        except Exception:
            replace_private_json(destination, {"operation": operation, "state": "failed_or_ambiguous",
                                               "instruction": "Reconcile remote writes before repeating; do not reuse this output"})
            raise

    def trigger_run(self, plan_id, journal, *, approve_execution=False, environment=None, preflight=None):
        positive_id(plan_id)
        if approve_execution is not True:
            raise core.Rejected("Saved-plan execution may bill; explicit --approve-execution is required")
        if environment is not None and (not isinstance(environment, str) or len(environment) > 500):
            raise core.Rejected("Invalid approved environment")
        event = {"state": "intent", "plan_id": plan_id, "transport": self.transport_label,
                 "environment_sha256": hashlib.sha256((environment or "").encode()).hexdigest(),
                 "non_idempotent": True, "stop_api": False}
        if preflight is not None:
            if not isinstance(preflight, dict) or preflight.get("checked") is not True or preflight.get("planId") != plan_id:
                raise core.Rejected("Project preflight does not match this plan")
            event["project_preflight"] = {key: preflight.get(key) for key in ("checked", "profileSha256", "observedSha256")}
        journal_event(journal, event, first=True)
        try:
            result = self._send("GET", f"/test_plans/{plan_id}/execution", {"environment": environment} if environment is not None else None)
            if not isinstance(result, dict):
                raise core.Rejected("Execution response did not contain a run ID")
            run_id = positive_id(result.get("id"))
            journal_event(journal, {"state": "accepted", "run_id": run_id, "plan_id": plan_id})
            return {"run_id": run_id, "state": "accepted", "transport": self.transport_label, "verdict": "inconclusive"}
        except Exception:
            journal_event(journal, {"state": "ambiguous", "instruction": "Reconcile in ContextQA; do not repeat this start"})
            raise core.Rejected("Execution acceptance is ambiguous; inspect the private journal and reconcile before any new start") from None

    def poll_run(self, run_id, *, max_attempts=20, interval=2, deadline=60, sleep=time.sleep, clock=time.monotonic):
        positive_id(run_id)
        if type(max_attempts) is not int or not 1 <= max_attempts <= 100 or not 0 <= interval <= 30 or not 0 < deadline <= 300:
            raise core.Rejected("Polling limits exceed local policy")
        began = clock()
        latest = None
        attempts = 0
        for index in range(max_attempts):
            remaining = deadline - (clock() - began)
            if remaining <= 0:
                break
            latest = self.call("getRunSummary", id=run_id, timeout=min(20, remaining))
            attempts += 1
            if not isinstance(latest, dict):
                raise core.Rejected("Unexpected summary response")
            if latest.get("status") == "STATUS_COMPLETED":
                break
            if index + 1 < max_attempts:
                remaining = deadline - (clock() - began)
                if remaining <= 0:
                    break
                sleep(min(interval, remaining))
        return {"run_id": run_id, "summary": latest, "attempts": attempts,
                "verdict": assessment(latest or {}), "polling_stopped": True,
                "upstream_cancelled": False, "transport": self.transport_label}


ARTIFACT_FIELDS = {"screenShotURL", "screenshotUrl", "snapshotUrl", "screenshots", "imageDifferenceUrl",
                   "visualRegImage", "screenRecordingUrl", "screenRecordings", "traceViewerUrl", "traceViewers",
                   "apiTraceViewerUrl", "logUrl", "reportFileUrl", "reports", "gifUrl", "gifs", "consoleLogs"}


def artifact_references(records):
    references = []
    def visit(value, field, origin, depth=0):
        if depth > 8:
            return
        if isinstance(value, str) and value.startswith("https://"):
            if len(references) >= 500:
                raise core.Rejected("Artifact reference count exceeds policy")
            references.append({"record": origin, "field": field, "url": value})
        elif isinstance(value, list):
            for index, item in enumerate(value[:500]):
                visit(item, field + "/" + str(index), origin, depth + 1)
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(item, field + "/" + str(key), origin, depth + 1)
    for origin, record in records:
        for field in ARTIFACT_FIELDS:
            if field in record:
                visit(record[field], field, origin)
    return references


def collect_results(client, root, run_id, case_ids=(), step_ids=(), suite_ids=(), *, plan_id=None, profile=None):
    root = Path(root)
    core.manifest(root)
    positive_id(run_id)
    selections = [list(case_ids), list(step_ids), list(suite_ids)]
    if any(len(items) > 100 or len(items) != len(set(items)) for items in selections):
        raise core.Rejected("Select unique bounded result IDs")
    for items in selections:
        for item in items:
            positive_id(item)
    summary = client.call("getRunSummary", id=run_id)
    if not isinstance(summary, dict):
        raise core.Rejected("Unexpected run summary")
    records = {}
    for kind, ids, operation in (("cases", case_ids, "getTestCaseResult"), ("steps", step_ids, "getTestStepResult"), ("suites", suite_ids, "getTestSuiteResult")):
        records[kind] = []
        for selected in ids:
            item = client.call(operation, id=selected)
            if not isinstance(item, dict) or type(item.get("id")) is not int or item.get("id") != selected:
                raise core.Rejected("Result response does not match selected ID")
            records[kind].append(item)
    cases = {item["id"]: item for item in records["cases"]}
    if any(type(item.get("testPlanResultId")) is not int or item.get("testPlanResultId") != run_id for item in cases.values()):
        raise core.Rejected("Case result does not attest selected run membership")
    for item in records["steps"]:
        parent = cases.get(item.get("testCaseResultId")) if type(item.get("testCaseResultId")) is int else None
        if parent is None or item.get("testCaseId") is not None and parent.get("testCaseId") != item["testCaseId"]:
            raise core.Rejected("Step result does not attest selected case membership")
    for item in records["suites"]:
        device = item.get("testDeviceResult")
        nested = device.get("testPlanResult") if isinstance(device, dict) else None
        if not isinstance(nested, dict) or type(nested.get("id")) is not int or nested.get("id") != run_id:
            raise core.Rejected("Suite result does not attest selected run membership")
    plan = run = None
    if plan_id is not None:
        positive_id(plan_id)
        run = client.call("getTestPlanResult", id=run_id)
        if not isinstance(run, dict) or type(run.get("id")) is not int or run.get("id") != run_id or type(run.get("testPlanId")) is not int or run.get("testPlanId") != plan_id:
            raise core.Rejected("Run does not attest selected plan membership")
        plan = client.call("getTestPlan", id=plan_id)
        if not isinstance(plan, dict) or type(plan.get("id")) is not int or plan.get("id") != plan_id:
            raise core.Rejected("Plan response does not match selected ID")
    if profile is not None:
        if not isinstance(profile, dict):
            raise core.Rejected("Approved capture profile must be a JSON object")
        validate(profile, {})
    private = core.private_dir(root / "private")
    data = {"run_id": run_id, "collected_at": now(), "transport": client.transport_label, "summary": summary,
            "plan_id": plan_id, "plan_snapshot": plan, "run_record": run, "capture_profile": profile, **records}
    refs = artifact_references([("summary", summary)] + [(kind + ":" + str(item["id"]), item) for kind, items in records.items() for item in items])
    core.write_json(private / "contextqa-results.json", data)
    core.write_json(private / "artifact-references.json", refs)
    return {"run_id": run_id, "case_results_read": len(cases), "step_results_read": len(records["steps"]),
            "suite_results_read": len(records["suites"]), "artifact_references": len(refs),
            "verdict": selected_assessment(data), "status": summary.get("status"), "result": summary.get("result"),
            "media_downloaded": False, "transport": client.transport_label, "paid_execution_started": False}


def import_result_steps(root):
    root = Path(root)
    data = core.load_json(root / "private" / "contextqa-results.json")
    steps = data.get("steps", [])
    if not steps or len(steps) > core.MAX_STEPS:
        raise core.Rejected("Collect explicit member step results before importing a guide")
    manifest = core.manifest(root)
    if manifest["steps"] or manifest.get("execution"):
        raise core.Rejected("Import result steps into a fresh empty workspace only")
    for item in steps:
        details = item.get("stepDetails") or {}
        observed = "Observed ContextQA result: " + str(item.get("result", "UNKNOWN")) + ". " + str(item.get("message", ""))
        manifest["steps"].append({"title": core.redact(details.get("stepDescription") or details.get("action") or "Step result " + str(item["id"])),
                                  "instruction": core.redact(observed), "media": [], "needs_review": True,
                                  "case_result_id": item["testCaseResultId"], "step_result_id": item["id"]})
    summary = data["summary"]
    manifest["execution"] = {"run_id": data["run_id"], "transport": data["transport"], "collected_at": data["collected_at"],
                             "status": summary.get("status"), "result": summary.get("result"), "verdict": selected_assessment(data),
                             "case_result_ids": [item["id"] for item in data["cases"]], "step_result_ids": [item["id"] for item in steps],
                             "source_sha256": core.export_digest(data), "media_downloaded": False}
    core.save(root, manifest)
    return {"imported_steps": len(steps), "requires_review": True, "media_attached": 0, "verdict": selected_assessment(data), "transport": data["transport"]}
