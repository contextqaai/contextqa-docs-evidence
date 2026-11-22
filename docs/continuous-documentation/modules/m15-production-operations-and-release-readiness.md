# M15 — Production operations and release readiness

A local implementation is in acceptance review. See the [working scope and remaining checks](../platform-acceptance.md). Upstream modules are M09 and M10.

## User outcome

The platform can run reliably for a real tenant with recoverable failures, controlled resource use and verifiable releases.

## Existing foundation

`Dockerfile; compose.yml; requirements-hosted.lock; historical test suites`

## Scope and workflow

Real OIDC, deployment/migrations, private artifact storage, retention, backup/restore, health/metrics/tracing, quotas, abuse controls, worker reconciliation, support diagnostics and rollback. Implement essentials throughout; final gate is after full loop.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Operational metrics, retention policy, usage ledger, audit records and release receipts. No self-service billing product required for pilot.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M15-T01:** Build deployment artifact and repeatable migration/rollback runbook.
- **M15-T02:** Add job/capture/delivery latency and failure alerts with correlation IDs.
- **M15-T03:** Implement tenant quotas, retention, credential rotation and artifact access checks.
- **M15-T04:** Exercise restore, worker death, source outage and rollback in staging.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Clean environment install, migration and worker startup succeed with recorded receipts.
- AC-2: Backup restore recovers guide versions, approval/delivery lineage and jobs.
- AC-3: Cross-tenant object/media access is rejected at every public surface.
- AC-4: Queued/inflight provider operations survive restart without duplicate charges/writes.
- AC-5: Defined retention deletes only eligible artifacts and keeps referenced published versions readable.

## ContextQA journey and reader guide

**Verify that a restored workspace can serve its approved guide.** As an operator in a disposable recovery environment, restore a known backup. Use ContextQA to open the restored guide as an authorized reader and match its version, figure and delivery lineage. Use sanitized frames in the internal recovery guide.

**Negative and recovery coverage.** Restart an in-flight job at a controlled boundary. Reconcile its external receipt, verify one operation, and pair the user journey with worker and restore receipts.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Proposed pilot targets: 99.5% monthly API availability, p95 metadata read under 1 s at 10 concurrent authors, RPO 24 h/RTO 4 h. These are targets to validate, not current guarantees.
