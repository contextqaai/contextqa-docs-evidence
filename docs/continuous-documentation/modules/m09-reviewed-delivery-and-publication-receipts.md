# M09 — Reviewed delivery and publication receipts

Status: planned; phase: Pilot. Dependencies: M02,M08.

## User outcome

An editor can deliver the exact reviewed content and know whether readers actually received it.

## Existing foundation

`loop_git.py; docs_loop.py package_bundle`

## Scope and workflow

GitHub PR create/update with Markdown/MDX, assets, navigation and metadata; explicit approval; remote baseline check; operation journal; reconciliation; merge/build/live status. Keep repository merge external for the first release. ZIP remains an export, never a publishing receipt.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

DeliveryIntent, FileManifest, ProviderReceipt, Publication; exact content/destination/approval digest; proposed deliveries APIs.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M09-T01:** Extend reviewed bundles to include verified media and structural changes.
- **M09-T02:** Wrap Git adapter as bounded worker operation with remote revision preflight.
- **M09-T03:** Reconcile lost responses and prevent duplicate PRs using operation metadata.
- **M09-T04:** Track PR merged SHA, build status and live-content verification separately.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Actual PR diff matches approved manifest; unrelated repo files are untouched.
- AC-2: New upstream changes block/rebase through review instead of force-writing.
- AC-3: Lost create response yields ambiguous state and provider lookup, not a duplicate PR.
- AC-4: PR creation/merge/build/live each have independent receipts; no premature Published badge.
- AC-5: Media links are durable destination references, not expiring evidence URLs.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred: in-app merge, scheduled publication and native help-center delivery until separately implemented. No automatic merge merely because tests pass.
