# M13 — Hosted docs reader, migrations and API reference

A local implementation is in acceptance review. See the [working scope and remaining checks](../platform-acceptance.md). Upstream modules are M03 and M09.

## User outcome

A customer can optionally host a branded, searchable documentation site with versions and controlled reader access.

## Existing foundation

`guides.py/library.py local HTML; not a hosted reader platform`

## Scope and workflow

Reader layout/search/TOC/navigation; brand and theme drafts; custom domains/TLS; versions/redirects; public/private reader access; GitBook/Fern/Intercom migrations; OpenAPI reference. Split into individual subprojects after core loop.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

DocsSite, Build, Domain, ReaderPolicy, Version, Redirect, ImportReport, ApiSpec; reader auth separate from author workspace membership.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M13-T01:** Ship reader rendering/search and immutable preview builds first.
- **M13-T02:** Add domain/TLS and publication configuration with explicit live states.
- **M13-T03:** Add docs/API versions, redirects and authenticated-reader access.
- **M13-T04:** Implement migrations and OpenAPI import with warnings and PR review.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Preview is revision-bound and never mislabeled live.
- AC-2: Private-site policy covers HTML, assets, search, Markdown and llms.txt on every hostname.
- AC-3: Redirect/path collision validation prevents cycles and broken navigation.
- AC-4: Migration reports skipped/failed content and preserves unrelated files.
- AC-5: Generated API pages derive from spec; direct editing cannot silently diverge.

## ContextQA journey and reader guide

**Preview a documentation version and follow its redirect.** As a site editor, preview a version-bound guide and verify its navigation and figure. As the intended reader, open the old path on the test site and follow it to the current guide. Capture preview identity and the reader destination.

**Negative and recovery coverage.** Try an unauthorized reader on a private site and verify access policy for both page and asset. Reject a redirect cycle before it reaches readers.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Reuse existing docs hosting in pilot. Four exact reference themes, upload-coming-soon controls and unused default-image settings are not requirements to reproduce.
