# M16 — Continuous product enablement assets

Status: planned; phase: Expansion. Dependencies: M10,M14.

## User outcome

Product changes propagate into accurate release notes, training, sales content and demo assets after owner review.

## Existing foundation

`approved guide versions and dependency graph`

## Scope and workflow

Audience-specific asset templates, approved-claim reuse, source-version badges, refresh proposals, owner approvals and destination adapters. Prioritize release notes and training text before decks/video. This comes from the user screenshot, not established Pageloop parity.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

EnablementAsset, Audience, AssetDependency, AssetVersion, OwnerReview, DistributionReceipt; shares approved source graph, not workspace-wide raw evidence.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M16-T01:** Create release-note and training-lesson templates using approved guide facts.
- **M16-T02:** Map each asset section to source guide/version and reviewed figure.
- **M16-T03:** Generate refresh proposals when dependent facts change.
- **M16-T04:** Add exports and one distribution destination with owner review and receipts.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: A changed claim marks only dependent assets stale.
- AC-2: Internal-only evidence and unapproved roadmap claims never leak into customer assets.
- AC-3: Stale assets remain labeled until reviewed refresh is published.
- AC-4: Regenerated asset preserves its audience and deliberate editorial overrides.
- AC-5: Distribution receipt is separate from draft generation and owner approval.

## ContextQA journey and reader guide

**Refresh a training lesson from an approved guide.** As an enablement owner, open an affected lesson, compare the changed claim against the approved guide, preserve the audience-specific edits and review the refreshed preview. Capture the dependency and before/after lesson.

**Negative and recovery coverage.** Change an internal-only claim and verify it is absent from the customer export. A failed export must preserve the prior distributed version and show its recovery action.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Do not execute the demo-factory prompts in the attachment. They are workflow inspiration; its runtime, credits and success claims do not establish this platform’s costs or readiness.
