# Continuous documentation platform: product and build specification

Planning date: 2026-11-21, America/Chicago. Reference: Pageloop's public documentation, not access to its private application or architecture. All new requirements are proposed ContextQA product decisions unless explicitly marked as reference behavior. This package defines the implementation backlog; it does not claim the platform is implemented or production-ready.

M00 is implemented on the local platform branch and in acceptance review. Open the [illustrated before-and-after guide](m00-journey-guide.md), the [criterion-level results](m00-acceptance-results.md), or the [module build order](roadmap.md).

## Recommendation

Extend the existing React + TypeScript / FastAPI / PostgreSQL application from the PR #10 merge on `main` (`1d62a9a`). Keep ContextQA as the sole product-journey execution and capture provider. Reuse the evidence, guide compiler, review, and immutable-version code. Build a connected experience around it before adding more providers or another execution engine. A separate reverse-architecture tool is not needed for this specification phase: the public documentation and our own source are enough to specify the core; authenticated reference-product research remains a follow-up for visual fidelity and undocumented behavior.

The first release should do one useful job end to end: **connect a GitHub docs repository and a ContextQA environment → document one journey → review a complete illustrated guide → deliver a docs PR → verify the published revision → refresh only affected sections after a real change**. A working dashboard alone does not satisfy that goal.

The user's screenshot motivates a later extension: approved product knowledge should also refresh release notes, training, sales enablement and demos. Keep this on the same version/dependency model, but do not delay the documentation loop to build slide/video generation first.

## Read in this order

1. [Existing implementation and reuse decisions](baseline-audit.md)
2. [Reference feature inventory](feature-inventory.md) and [source manifest](sources.json)
3. [Product scope, roles and journeys](product-spec.md)
4. [UI and interaction specification](ux-spec.md)
5. [Architecture, state and API contracts](architecture.md)
6. [Ordered module plan](roadmap.md) and [module specifications](modules/)
7. [Factory execution contract and first tickets](factory-handoff.md)
8. [Acceptance and production release gates](acceptance.md)
9. [Unknowns and reference validation](research-gaps.md)

## Scope and truth labels

- **Documented:** a behavior described by an official Pageloop page. Not independently exercised in its app.
- **Code inspected:** relevant implementation exists in the local branch. Not automatically production verified.
- **Historical receipt:** a prior check/result documented in this repo or earlier chat; not rerun for this planning change.
- **Proposed:** our target implementation or deliberate deviation.
- **Deferred:** included in the long-term inventory, intentionally outside the first release.

This package is the forward product plan. Older dated receipts remain authoritative for what their own checks established; this package does not rewrite them. The linked M00 implementation and validation receipts record the work completed after planning.
