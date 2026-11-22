# M06 — ContextQA journey discovery, execution and capture

Status is in development. The [capture implementation and results](../m06-results.md) cover the hosted worker, replay UI and open pilot gates. Dependencies are M01 and M04.

## User outcome

A user supplies URL, goal and credential reference, then obtains repeatable saved journeys and trustworthy capture evidence.

## Existing foundation

`journeys.py; writer.py; frames.py; examples/orangehrm`

## Scope and workflow

ContextQA workspace/environment binding, saved journey selection or prompt bootstrap, coverage plan, replay, deployment validation, capture checkpoints and diagnostics. All product journeys and workflow-proof media come from ContextQA. Never substitute a local browser recording as acceptance evidence.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

JourneyVersion, CoverageRequirement, CapturePlan, ProviderOperation, EvidenceArtifact; explicit upstream IDs and definition/deployment digests; private credential references only.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M06-T01:** Expose existing registry/profile selection and configuration drift in a setup UI.
- **M06-T02:** Bootstrap bounded journeys from URL + goal using supported ContextQA tools; track uncovered requirements.
- **M06-T03:** Independently replay generated saved steps; repair only demonstrated brittle assertions.
- **M06-T04:** Integrate journalled execution, bounded polling, artifact collection and capture review into durable worker.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Bootstrap success and saved-case replay success are independently displayed.
- AC-2: Unknown deployment commit is labeled; release-bound publication is blocked when binding is required.
- AC-3: Failed/inconclusive/stale results cannot advance an approved guide.
- AC-4: Ambiguous accepted trigger causes reconciliation, never an automatic second run.
- AC-5: Every figure resolves to actual run/case/step or verified recording frame and checksum.
- AC-6: A missing balance/permission prerequisite appears as not covered, even if the exploration step passed.

## ContextQA journey and reader guide

**Record and replay a documentation journey.** As a capture owner, select the environment, bind the intended build, save the journey and replay it. Capture the coverage report and one approved figure with its source step. Verify the independent replay result.

**Negative and recovery coverage.** Use a controlled target revision mismatch or omit a prerequisite. Verify the exact coverage gap and that the previous approved guide remains current.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Current historical contract has non-idempotent run start and no stop API. Confirm current provider contract during implementation; never invent cancellation or a cost cap.
