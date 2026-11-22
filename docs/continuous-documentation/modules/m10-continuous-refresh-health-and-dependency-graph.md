# M10 — Continuous refresh, health and dependency graph

Status: planned; phase: Pilot. Dependencies: M04,M09.

## User outcome

A shipped change refreshes affected guidance while preserving the latest good version when anything fails.

## Existing foundation

`guides.py impact; library.py; HealthReport`

## Scope and workflow

Section/claim/figure dependencies, source/deployment freshness, scheduled scans, selective recapture/redraft, before/after comparison, no-op detection and remediation. Keep age-based checks separate from factual validation.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

DependencyEdge, RefreshPlan, HealthFinding, GuideVersion, LatestApproved pointer; proposed dependencies/health APIs.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M10-T01:** Persist source-to-claim/section/figure dependency edges.
- **M10-T02:** Calculate affected scope and wait for required deployment binding.
- **M10-T03:** Run only selected journeys and regenerate affected sections with immutable versions.
- **M10-T04:** Expose findings, comparison and refresh receipt without hiding failures.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Unchanged source/evidence creates no content update.
- AC-2: Controlled real UI change updates correct text and image; unrelated section remains intact.
- AC-3: Failed capture leaves latest approved pointer unchanged and shows stale-warning reason.
- AC-4: Concurrent finalization cannot regress latest version.
- AC-5: A timestamp-only change does not imply a reader-visible change.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Semantic visual comparison is proposed and must have evaluated false-positive behavior; hashes alone are not semantic detection.
