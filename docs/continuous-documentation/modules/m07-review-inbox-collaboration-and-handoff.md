# M07 — Review inbox, collaboration and handoff

Status: planned; phase: Pilot. Dependencies: M01,M05.

## User outcome

A reviewer can understand, decide and hand off work without losing edits or confusing review with publication.

## Existing foundation

`Review.tsx; InboxPage; loop.py`

## Scope and workflow

Open/Assigned/Resolved/Archived, priority and reasons, search, bulk actions, item/page views, contextual evidence, question rounds, comments and role-safe handoff. Keep run state separate from review and delivery state.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

ReviewItem, Assignment, CommentThread, ReviewDecision, QuestionRound, NotificationOutbox; revision-checked mutation APIs.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M07-T01:** Extend inbox data model for archive/resolve/priority and paginated selection.
- **M07-T02:** Implement change/article/evidence/activity review and clearly scoped bulk decisions.
- **M07-T03:** Add question rounds and comments anchored to item/change; preserve source references.
- **M07-T04:** Implement ready-for-publish recipient/note and notification receipt.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Contributor search/counts/exports contain assigned items only.
- AC-2: Item Accept all and page Accept all apply exactly their stated scope.
- AC-3: A stale review version fails without overwriting another reviewer.
- AC-4: Handoff persists edits and decisions, reassigns once, and removes former contributor access.
- AC-5: Resolve/archive/accept never publishes; partial bulk failure reports affected items.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred: destructive permanent deletion UI until dependency cleanup and audit semantics are defined. Archive is sufficient for pilot.
