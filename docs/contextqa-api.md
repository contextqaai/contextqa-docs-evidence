# ContextQA API to reviewed documentation

ContextQA supplies saved tests, execution and result records. This package supplies an explicit local client, run journal, result selection and reviewed Markdown/HTML output. AI drafting is optional and is **not** the browser execution engine.

Implemented locally against the supplied API-token OpenAPI 3.0.3/version 1.0.0 contract (SHA-256 `e8b3afefcb6eba18172081a8daad8f962cb28a95a284a33acb3369ff928531fa`). Contract availability and live tenant acceptance are different: no live token, billed run or provider key was used in implementation tests. The generated [operation/schema subset](../cqa_artifacts/contextqa-contract.json) supports 26 JSON operations relevant to authoring and documentation plus the separately guarded saved-plan GET trigger. It deliberately omits system audits, presigned uploads and multipart mobile execution; there is no arbitrary endpoint escape hatch.

See the shared [ContextQA platform configuration map](contextqa-platform.md) for environment/data/prerequisite/suite/plan/browser/parallel boundaries.

## Start without an account

```sh
python3 -m unittest discover -s tests -v
python3 examples/contextqa_demo.py /tmp/NEW-contextqa-guide-simulation
python3 -m cqa_artifacts contextqa-operations
```

Choose a new directory. The demo uses an injected transport with contract-shaped synthetic responses: case → step → suite → plan authoring, one journalled start, polling, selected result collection, private plan/profile snapshot and reviewed guide export. It makes **zero network, browser, model or billed calls**. The resulting HTML/Markdown visibly says **SIMULATED TRANSPORT**. No screenshot is invented or downloaded; image/video URLs exist only in the private references manifest. This is an API integration exercise, not proof of a real test passing.

## Obtain and scope a token

The supplied contract says a **superadmin** creates a token in the ContextQA application at **Settings → API tokens**. The wire format is `Authorization: Bearer token_<tenant>.<secret>` and the token selects the tenant; no tenant header is added. New signup entitlement, token-creation UX and applicable pricing still need account-specific confirmation. Do not promise that every signup grants immediate API access.

Inject `CONTEXTQA_API_TOKEN` from a secret manager or private process environment. The CLI has no token argument. Do not paste a token into issue text, a JSON DTO, screenshot, shell command line or repository. `CONTEXTQA_API_TOKEN` is separate from the Browser Cloud pilot key and from `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. Ordinary `python` does not automatically load `.env`.

Use least privilege, adding authoring/execution scopes only when needed:

| Purpose | Implemented endpoint family | Exact permission |
|---|---|---|
| List/read cases; create/update/patch | `GET/POST /test_cases`; `GET/PUT/PATCH /test_cases/{id}` | `TEST_CASES_READ` / `TEST_CASES_WRITE` |
| List/read/create/update steps | `GET/POST /test_steps`; `GET/PUT /test_steps/{id}` | `TEST_STEPS_READ` / `TEST_STEPS_WRITE` |
| List/read/create/update suites | `GET/POST /test_suites`; `GET/PUT /test_suites/{id}` | `TEST_SUITES_READ` / `TEST_SUITES_WRITE` |
| List/read/create/update plans | `GET/POST /test_plans`; `GET/PUT /test_plans/{id}` | `TEST_PLANS_READ` / `TEST_PLANS_WRITE` |
| Start a saved plan | **`GET /test_plans/{id}/execution`** | `TEST_PLAN_EXECUTE` |
| List/read plan results and summary | `GET /test_plan_results`; `GET /test_plan_results/{id}`; `GET /test_plan_results/{id}/results` | `TEST_PLAN_RESULTS_READ` |
| List/read suite results | `GET /test_suite_results`; `GET /test_suite_results/{id}` | `TEST_SUITE_RESULTS_READ` |
| List/read case results | `GET /test_case_results`; `GET /test_case_results/{id}` | `TEST_CASE_RESULTS_READ` |
| List/read step results | `GET /test_step_results`; `GET /test_step_results/{id}` | `TEST_STEP_RESULTS_READ` |

The client fixes its base to `https://server.contextqa.com`, disables environment proxy forwarding and rejects redirects. It does not support a dedicated/on-prem override in this version. The contract states 120 requests/minute/token, optional IP allowlists and `429` with `Retry-After` seconds. Shared-token traffic can still exceed that limit. Each real client spaces request starts by at least about 0.55 seconds (roughly 109/minute); simulated transport has no wait. This is per instance, not an aggregate limiter across processes or applications sharing a token. The client makes one request per call and never retries, including reads. After a rate limit, respect the server delay before a separately initiated safe read; **never treat this as permission to repeat a start**.

## Read and author reviewed ContextQA objects

`contextqa-operations` prints supported operation IDs, methods, paths and scopes without requiring credentials. Read one page or one object and save its full response privately:

```sh
python3 -m cqa_artifacts contextqa-call --operation listTestPlans --out private/plans-page-1.json
python3 -m cqa_artifacts contextqa-call --operation getTestPlan --id PLAN_ID --out private/plan.json
```

Replace uppercase IDs with actual integers. Lists explicitly default to `size=50,page=0` (important because steps otherwise default to unpaged). A JSON `--query FILE` may supply documented `query`, `page`, `size`, `sort` and the step group flags where supported. Local bounds: size 1–100, page 0–10000; no automatic pagination or whole-tenant crawl. Responses are private files; terminal receipts omit bodies and artifact URLs.

Authoring is explicit and schema-validated:

```sh
python3 -m cqa_artifacts contextqa-call --operation createTestCase --body private/reviewed-case-request.json --approve-write --out private/created-case.json
python3 -m cqa_artifacts contextqa-call --operation updateTestPlan --id PLAN_ID --body private/reviewed-plan-request.json --approve-write --out private/updated-plan.json
```

Use the generated request DTOs and an authorized existing workspace. Top-level/nested documented types and enums are checked; unknown defined DTO fields are rejected. Fields with deliberately open object schemas stay open under size/depth bounds. The contract has few required business fields; passing local validation is not proof the tenant will accept or execute an object. The server can still reject missing relations or unsupported natural-language semantics. A successful object write is not a successful test run. No write is retried; reconcile uncertain creation in ContextQA before repeating it. CLI output destinations must be new. An exclusive owner-only intent file is fsynced before remote authoring, then replaced by the response or a failure/ambiguous receipt. The same output cannot be reused to repeat a write. A new filename does not make an uncertain write safe to retry.

Use existing ContextQA configuration rather than recreating a framework here:

- Cases can reference `testDataId`, prerequisite case IDs, environment and recording options; steps include `testDataId`, `testDataProfileStepId`, prerequisite step IDs and the contract's misspelled `exceptedResult`.
- Suites can group `testCaseIds` and prerequisites. Plans can carry `environmentId`, `parallelNode`, `testPlanType`, screenshot/recovery/rerun settings and `testDevices` with browser/platform/suite mappings.
- These are supported DTO fields, not proof that every account, browser, lab, data profile or parallel capacity is enabled. Resolve IDs and edit environment/data/lab configuration in the authorized ContextQA UI. The supplied contract has **no environment/data-profile CRUD endpoint**. Do not invent one.
- Before a real run, review the selected plan, suites/cases/steps, prerequisites, seed data, browser/device matrix, environment and server-side rerun/notification settings. Plan-internal retries can still cause extra work even though this client never retries the trigger.

## Check reusable project configuration

Copy `examples/contextqa-project.example.json` into private storage and replace its fictional IDs and expectations with authorized ContextQA values. The same profile shape is used across the related repositories. Do not run the example IDs against a real tenant.

```sh
python3 -m cqa_artifacts contextqa-project-check --profile private/approved-project.json --out private/project-check.json
python3 -m cqa_artifacts contextqa-run --plan-id PLAN_ID --profile private/approved-project.json --journal private/NEW-profile-run.jsonl --approve-execution
```

`contextqa-project-check` reads the selected saved plan and explicit cases/suites/steps, compares the expected subset, and writes observed/profile hashes privately. Arrays must match expected length/order. Drift blocks the check without starting execution. `contextqa-run --profile` repeats this read-only preflight before its single start, requires the same plan ID and rejects a conflicting explicit environment. Only the approved environment query is supported in this documentation runner. The journal records preflight hashes; this is not an upstream configuration lock, and a server-side edit after checking remains possible. Without `--profile`, the operator must perform equivalent plan review; no automatic configuration-verification claim is made.

This checked project profile differs from `contextqa-collect --profile`, which records supplied capture context after a run without automatically proving that context.

## Start once, then poll the accepted run

This GET is a side effect and may bill. It is intentionally unavailable through `contextqa-call`; do not turn it into a clickable preview or prefetch it.

```sh
python3 -m cqa_artifacts contextqa-run --plan-id PLAN_ID --environment APPROVED_ENVIRONMENT --journal private/NEW-run.jsonl --approve-execution
python3 -m cqa_artifacts contextqa-poll --journal private/NEW-run.jsonl --max-attempts 20 --interval 2 --deadline 60 --out private/run-poll.json
```

The approval flag means the operator has authorized this exact plan/environment and its potential charge. It is not a budget cap, automatic entitlement or approval on someone else's behalf. Omit `--environment` only after reviewing the saved plan default.

The journal is exclusive and owner-only. It records and fsyncs intent plus its directory entry **before sending**, then durably records the returned positive run ID **before polling**. Existing journals are never reused to start again. A timeout, malformed response or persistence error after sending is **ambiguous acceptance**, not rejection: inspect the private journal and reconcile in ContextQA. Do not create a new journal to bypass this hold. This is a local single-user control; upstream exactly-once execution is not guaranteed.

Polling reads only the accepted result. It is bounded to at most 100 attempts, a 300-second best-effort local scheduling deadline, a socket-operation timeout up to 20 seconds and configurable 0–30-second intervals; defaults above use 20 attempts/60 seconds. Python urllib socket timeouts and request spacing are not a hard wall-clock kill; a response that makes intermittent progress can exceed the scheduling deadline. Stopping polling **does not stop the run**. The token contract exposes no stop/cancel endpoint and no documented server budget cap. Paid execution pricing, failed-run charging, concurrency and total runtime remain unverified; do not start a live experiment without an owner-approved cost envelope.

`passed` requires `STATUS_COMPLETED`, `SUCCESS`, a positive integer total, every required count present/consistent, passed=total, and zero failed/aborted/stopped/not-executed/queued counts. Completed `FAILURE`, `ABORTED` or `STOPPED` is `failed`. All other combinations, including missing or contradictory counts, are `inconclusive`; original status/result remain available. Poll CLI exits 0 for passed, 2 for failed/inconclusive and 1 for input/transport errors. Other commands' exit 0 means the requested processing completed, not that a test passed.

## Collect selected results into a reviewed guide

Create a new empty workspace, then select known result IDs. List/read commands help inspect identifiers; no undocumented query grammar or automatic case discovery is assumed.

```sh
python3 -m cqa_artifacts init workspaces/live-guide --title 'Reviewed ContextQA workflow'
python3 -m cqa_artifacts contextqa-collect workspaces/live-guide --run-id RUN_ID --plan-id PLAN_ID --case-result-id CASE_RESULT_ID --step-result-id STEP_RESULT_ID --profile private/capture-profile.json --import-steps
```

Repeat the case/step flags for more selected records. Optional `--suite-result-id` requires the returned suite's `testDeviceResult.testPlanResult.id` to attest the same run. Case results must explicitly identify the run; steps must explicitly identify a selected case and match test-case identity when present. Mismatches/missing relationships fail closed. With `--plan-id`, the run's `testPlanId` must match before `getTestPlan` is saved; conflicting run-record/summary status/result/counts prevent pass. The fetched plan is current configuration, not proof of its exact historical values at execution time; retain and review the run record too. Boolean IDs, duplicate IDs and selections over 100 per kind are rejected.

The full raw summary/selected records, plan snapshot and supplied capture profile remain in `workspace/private/contextqa-results.json`. A profile can record application version, role, viewport, environment/data IDs and intended browser matrix, but **is operator-supplied context**: it is neither automatically compared with the plan nor forwarded as runtime configuration. Review actual result/plan values before claiming the intended matrix ran. Cross-browser/parallel execution is performed by the saved ContextQA configuration, not by this wrapper creating local browsers.

Known screenshot/snapshot/video/trace/API-trace/log/report/GIF/console-reference fields are gathered into a separate private manifest, including nested `screenshots` values. Signed references are credentials. No host list or artifact-download authentication contract was supplied, so **remote media retrieval is deliberately not implemented**. Obtain permitted media through a reviewed first-party flow, inspect it and use `add-media`/`attach`. Do not forward the bearer to storage or follow arbitrary media URLs.

`--import-steps` copies redacted observed result text into candidate guide steps and preserves case/step/run IDs, transport label, timestamp and source digest. It requires an empty workspace. Imported steps **need human review** and have no attached screenshot. Review and edit each instruction, attach actual reviewed media if available, then run `approve` and `export` as in the README. Guide JSON/Markdown/HTML preserve the public result provenance, while private URLs/raw records remain excluded. A summary pass cannot hide a selected failure or unknown selected outcome. A result reference does not establish that an image exists or that the reader may see it.

For refresh, recapture the same selected saved workflow under two documented versions/environments, create separate reviewed exports, and compare explicit step mappings. The existing `compare` behavior is text/media identity comparison, not automatic release mapping or semantic visual regression. Never overwrite the baseline.

## Tests and boundaries

The tests exercise every one of the 26 catalog routes with mocked transport, schema/permission flags, bounded queries/responses, secret/error suppression, journal order/reuse/ambiguity, strict verdicts, parent mismatches, artifact-reference privacy and simulated API-to-guide export. The separate real-media test in [real-testing.md](real-testing.md) exercises actual screenshot packaging, not SaaS API acceptance. Current live tenant, metering, data-profile, prerequisite, browser-matrix and parallel-capacity acceptance remain unperformed. Native Layerpath/EkLine publication remains a separate task.
