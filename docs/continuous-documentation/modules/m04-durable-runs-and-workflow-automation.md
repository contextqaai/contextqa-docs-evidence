# M04 — Durable runs and workflow automation

Status: planned; phase: Pilot. Dependencies: M02,M03.

## User outcome

A writer can configure a repeatable job, test it, and understand what ran after a restart.

## Existing foundation

`existing event ingestion; no durable hosted scheduler currently`

## Scope and workflow

Durable jobs, leases, stage receipts, workflow versions, merged-PR/scheduled triggers, pause/activate, explicit backlog handling, test runs and run history. Use timezone-aware schedules. Research/drafting schedule is distinct from publication schedule.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Workflow, WorkflowVersion, Run, JobAttempt, SourceCursor; proposed workflows/runs endpoints with expected_version and internal idempotency key.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M04-T01:** Build Postgres queue, lease recovery and stage checkpoints.
- **M04-T02:** Implement trigger validation, persisted versions and scheduler with timezone/DST policy.
- **M04-T03:** Build workflow instructions and history UI with test/activate/pause.
- **M04-T04:** Implement safe retry classification, input questions and backlog process/skip.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Worker restart resumes from persisted stage without duplicated external writes.
- AC-2: Editing a live workflow leaves current run on its pinned version.
- AC-3: Pausing prevents new dispatch while accepted remote work stays visible.
- AC-4: Test run does not advance live cursor or publish/send notifications; one test in flight per workflow.
- AC-5: Missing source/invalid schedule/budget stop identifies the precise remediation.
- AC-6: DST tests cover repeated and skipped local times with one documented dispatch policy.

## ContextQA journey and reader guide

**Test a workflow before activating it.** As a workflow owner, configure a test trigger, run it, inspect its version and stage timeline, then return to the workflow. Capture the test configuration and completed sample run.

**Negative and recovery coverage.** Check that the test leaves the live cursor unchanged. In a disposable job, restart the worker and verify it resumes at the persisted stage without a duplicate external write.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Proposed scheduling policy: run once at the next valid local instant for skipped time; once for repeated time. Remote non-idempotent capture start never inherits generic queue retry.
