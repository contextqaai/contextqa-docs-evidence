# M08 — Article editor, change sets and conflict resolution

A local implementation is in acceptance review. See the [working scope and remaining checks](../platform-acceptance.md). Upstream modules are M03 and M07.

## User outcome

A writer can revise text and related assets/navigation as one coherent, versioned proposal.

## Existing foundation

`Review.tsx; loop.py approval/baselines`

## Scope and workflow

Source/visual editing, metadata, clean final preview, typed body/new/delete/move/navigation/image operations, granular decisions, autosave, three-way conflicts and rendered preview. Pilot can start with source editor plus accurate preview; full block editing is later within this module.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

ChangeSetEntry operation enum; base/draft/upstream hash; navigation/config versions; review generation. Generated API pages remain source-spec controlled.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M08-T01:** Define typed entries and accepted-output assembly with dependencies.
- **M08-T02:** Implement source editor, safe MDX rendering, save/dirty state and clean preview.
- **M08-T03:** Add navigation/metadata/media proposals and invalid-reference detection.
- **M08-T04:** Implement drift classification and person-resolved overlapping edits.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Rejected/pending changes never leak into accepted-result preview or delivery.
- AC-2: An image addition required by an accepted page cannot be omitted silently.
- AC-3: Upstream move/delete/address collision preserves local draft and offers explicit resolution.
- AC-4: Content/media/metadata changes invalidate approval and old preview.
- AC-5: Editing then refresh/failed save/conflict never silently loses text.

## ContextQA journey and reader guide

**Edit an article and preview its approved changes.** As an editor, change a paragraph and its figure, save, reload, and inspect the accepted-result preview. Capture the diff and the matching rendered section.

**Negative and recovery coverage.** Make an overlapping edit from a second revision. Verify the conflict preserves both inputs, resolve it, and confirm the earlier approval is invalidated.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred block palette: callouts/cards/tabs/steps/accordions/tables/diagrams with safe syntax. No arbitrary MDX evaluation.
