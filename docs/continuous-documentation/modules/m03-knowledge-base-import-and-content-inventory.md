# M03 — Knowledge-base import and content inventory

Status: implemented locally and in acceptance review. Phase: Pilot. Depends on M02. See the [acceptance report](../m03-results.md) and [illustrated guide](../m03-walkthrough.md).

## User outcome

A writer can see the real existing docs and select a topic without pasting Markdown manually.

## Existing foundation

`loop.py article baselines; pages.tsx Articles; agent manifest`

## Scope and workflow

GitHub Markdown/MDX import, branch/root validation, article inventory, stable identity/path mapping, search and navigation import. Preview inventory before import; preserve existing content on partial reads. Initial UI may remain a simple tree plus source preview.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Article, ArticleVersion, NavigationSnapshot, ImportJob; proposed imports and paginated articles APIs. Baselines retain source commit/content digest.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M03-T01:** Inventory selected docs root and detect supported config format.
- **M03-T02:** Show import preview with pages/assets/navigation, collisions and unsupported components.
- **M03-T03:** Persist per-item progress and resume/retry failures without duplicate articles.
- **M03-T04:** Add search, page tree and source-version details to knowledge base.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Nested paths, same-title pages and local image links import with stable IDs.
- AC-2: A partial provider listing never deletes previously known articles.
- AC-3: Invalid MDX/config is reported per file; no arbitrary code is evaluated.
- AC-4: Reimport unchanged source is a no-op; changed source creates a new baseline version.
- AC-5: Reader-facing links, navigation location and repository path are modeled separately.

## ContextQA journey and reader guide

**Import and find an existing article.** As an editor, import a nested docs tree with same-title pages. Open the intended path, inspect its local figure and capture the inventory and imported preview.

**Negative and recovery coverage.** Interrupt the listing and verify that known pages remain. Complete the sync and repeat it with identical input to verify stable identities and no extra baseline.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred: Intercom/GitBook/Fern migrations and OpenAPI generation to M13; publish no automatic conversion claims.
