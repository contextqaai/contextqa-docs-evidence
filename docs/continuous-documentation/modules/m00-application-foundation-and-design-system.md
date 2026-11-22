# M00 — Application foundation and design system

Implemented on the local platform branch and in acceptance review. See the [Ship 5 journeys and criterion-level findings](../m00-acceptance-results.md) and the [route audit](../m00-implementation.md).

## User outcome

A writer can navigate a coherent workspace and recover from loading, save and permission failures.

## Existing foundation

`apps/web/src/App.tsx; components.tsx; style.css; existing hosted API`

## Scope and workflow

App shell, workspace navigation, Home, shared forms/dialogs/tables and all standard states. Split the dense existing page files into maintainable components without changing evidence gates. Do not build a cosmetic dashboard with disconnected mock data.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

No new domain tables; route/workspace state and shared view models. Keep current /api/projects and scoped state until paginated resources replace them.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M00-T01:** Audit existing routes and UI states; map each to ux-spec.md.
- **M00-T02:** Extract tokens, shell, navigation and accessible primitives; retain ContextQA logo.
- **M00-T03:** Implement Home using actual queue/run summaries with honest empty states.
- **M00-T04:** Add route restoration, pending-action handling, accessible errors and responsive review shell.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: At 1440, 1024 and 390 px, every primary action remains reachable without page-level horizontal overflow.
- AC-2: Switching workspace clears prior scoped data before rendering the next workspace.
- AC-3: Failed load shows retry; zero records shows a first-use action; neither is shown as success.
- AC-4: Keyboard users can navigate menus/dialogs; focus returns to the initiating control.
- AC-5: Existing review/edit/save behavior and approval invalidation remain unchanged.

## ContextQA journey and reader guide

**Find a request and check its evidence.** As an editor, open the overview, select the seeded request, inspect source and execution evidence, and return to the queue. Capture the request summary and evidence tab. On a phone, capture the article selector with the selected path.

**Negative and recovery coverage.** Reject an invalid sign-in and verify the request is hidden. Recover access and check the same request. The current receipt records additional gaps for switching workspaces, keyboard menus and writable saves.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred: new integrations, model calls and paid capture. Risk: component refactoring breaks existing dirty-state behavior.
