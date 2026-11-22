# M12 — Additional source and help-center integrations

Status: planned; phase: Parity. Dependencies: M02,M09.

## User outcome

A customer can keep existing help-center infrastructure and use issue/support evidence without an all-or-nothing migration.

## Existing foundation

`ContextQA and GitHub foundations; other adapters not inspected as implemented`

## Scope and workflow

Separate source and destination capability adapters. Order: one demanded provider first, then GitLab/Linear/Jira/Slack; Intercom/Freshdesk/Help Scout/Document360/Pylon; remaining documented providers only on demand. See connector-matrix.md.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Provider capability descriptor, cursor, external version, article/container mapping, per-operation delivery receipt. One active docs destination per site; ticket source assigned separately.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M12-T01:** Define adapter capabilities and contract fixtures before provider implementation.
- **M12-T02:** Implement one provider end to end: connect/scope/read/draft/review/deliver/reconcile.
- **M12-T03:** Add provider-specific warnings, reconnect and partial-sync recovery.
- **M12-T04:** Repeat as separate provider tickets, not a blanket all-integrations story.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Connected but unconfigured has a clear finish-setup state.
- AC-2: Selected scope is enforced in backend reads, not only prompt guidance.
- AC-3: Provider Draft mode discloses any immediate metadata/structural effects.
- AC-4: Missing results during partial sync do not mass-delete content.
- AC-5: Partial delivery retries only confirmed failed operations; unknown creation is reconciled.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Do not assume APIs/entitlements from Pageloop integration pages. Read each provider’s current contract before implementing. Legacy Mintlify tile is not a new connector to copy.
