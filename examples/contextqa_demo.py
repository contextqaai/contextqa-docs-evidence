"""Contract-shaped ContextQA transport simulation. No live API, browser or AI."""
import json
from pathlib import Path
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cqa_artifacts import core
from cqa_artifacts.contextqa import ContextQAClient, collect_results, import_result_steps


SUMMARY = {"status": "STATUS_COMPLETED", "result": "SUCCESS", "totalCount": 1,
           "passedCount": 1, "failedCount": 0, "abortedCount": 0, "stoppedCount": 0,
           "notExecutedCount": 0, "reportFileUrl": "https://artifacts.example/report?signature=SIMULATED_PRIVATE"}
CASE = {"id": 902, "testCaseId": 41, "testPlanResultId": 901, "suiteResultId": 904,
        "status": "STATUS_COMPLETED", "result": "SUCCESS", "screenRecordingUrl": "https://artifacts.example/demo.webm?signature=SIMULATED_PRIVATE"}
STEP = {"id": 903, "testCaseResultId": 902, "testCaseId": 41, "result": "SUCCESS",
        "message": "Simulated assertion: the seeded project name was displayed.",
        "stepDetails": {"stepDescription": "Confirm the synthetic project name", "exceptedResult": "Synthetic project is displayed"},
        "screenShotURL": "https://artifacts.example/demo.png?signature=SIMULATED_PRIVATE"}
SUITE = {"id": 904, "status": "STATUS_COMPLETED", "result": "SUCCESS",
         "testDeviceResult": {"testPlanResult": {"id": 901}}}
PLAN = {"id": 44, "name": "Synthetic documentation capture", "environmentId": 11,
        "parallelNode": 2, "testPlanType": "CROSS_BROWSER",
        "testDevices": [{"browser": "chrome", "planSuites": [{"suiteId": 43, "orderIndex": 0}]},
                        {"browser": "firefox", "planSuites": [{"suiteId": 43, "orderIndex": 0}]}]}


def main(destination):
    destination = Path(destination)
    if destination.exists():
        raise core.Rejected("Choose a new simulation directory")
    calls = []
    def transport(request, timeout, limit):
        path = urllib.parse.urlsplit(request.full_url).path
        calls.append({"method": request.method, "path": path})
        if request.method in ("POST", "PUT", "PATCH"):
            body = json.loads(request.data)
            ids = {"/test_cases": 41, "/test_steps": 42, "/test_suites": 43, "/test_plans": 44}
            return json.dumps(dict(body, id=ids[path])).encode()
        data = {"/test_plans/44/execution": {"id": 901}, "/test_plan_results/901/results": SUMMARY,
                "/test_case_results/902": CASE, "/test_step_results/903": STEP,
                "/test_plan_results/901": {"id": 901, "testPlanId": 44}, "/test_plans/44": PLAN}
        if path not in data:
            raise AssertionError("Unexpected simulated operation")
        return json.dumps(data[path]).encode()
    client = ContextQAClient("token_demo.simulated", transport=transport, simulated=True)
    # Synthetic DTOs show relationships, not universal runnable NLP semantics.
    client.call("createTestCase", body={"name": "Synthetic project check", "workspaceVersionId": 1, "testDataId": 21,
                "prerequisiteTestCaseIds": [31], "captureAllStepScreenshots": True}, approve_write=True)
    client.call("createTestStep", body={"testCaseId": 41, "position": 1, "type": "NLP_TEXT", "action": "Confirm the seeded project name",
                "exceptedResult": "Synthetic project is displayed", "testDataProfileStepId": 21}, approve_write=True)
    client.call("createTestSuite", body={"name": "Synthetic suite", "testCaseIds": [41], "workspaceVersionId": 1, "preRequisite": 30}, approve_write=True)
    client.call("createTestPlan", body={key: value for key, value in PLAN.items() if key != "id"}, approve_write=True)
    journal = destination / "private" / "run.jsonl"
    client.trigger_run(44, journal, approve_execution=True, environment="synthetic-staging")
    polled = client.poll_run(901, max_attempts=1)
    workspace = destination / "workspace"
    core.init(workspace, "SIMULATED ContextQA run — project guide")
    collected = collect_results(client, workspace, 901, [902], [903], plan_id=44,
                                profile={"environmentId": 11, "dataProfileId": 21, "version": "synthetic-A", "viewport": "1280x800"})
    imported = import_result_steps(workspace)
    core.edit_step(workspace, 1, "Confirm the synthetic project name", "Simulated result: the seeded project name was displayed. No real browser was executed and no screenshot was downloaded.")
    core.approve(workspace, "Synthetic fixture review only; not customer approval", True)
    exported = core.export(workspace, destination / "guide", "https://docs.example.com/simulated-contextqa")
    receipt = {"transport": "simulated", "live_api_calls": 0, "browser_executed": False, "model_calls": 0,
               "simulated_requests": len(calls), "poll": polled["verdict"], "collection": collected,
               "import": imported, "export": exported, "media_downloaded": False}
    core.write_json(destination / "receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
