# Completing the ContextQA documentation lifecycle

Core completion does not require Layerpath or EkLine. They are optional destinations
for clients who use those tools, not execution producers or prerequisites. Earlier
requirements to demonstrate both native platforms are superseded by the
[ContextQA-led usage guide](how-to-use.md) and [trigger design](documentation-triggers.md).

## Core acceptance

| Stage | Evidence required |
| --- | --- |
| Onboarding | Correct tenant/workspace, application URL, authorized auth mechanism and reviewed generated test/workflow scope |
| Documentation structure | Stable section IDs linked to workflows/tests; optional module/code mapping; owner and coverage gaps |
| Client instructions | Owner-reviewed version/hash; audience, brand, dos/don'ts and review policy; automatic loading not implied |
| Baseline capture | Real ContextQA terminal/per-step results, selected media, role/environment/date and verified revision or explicit unknown |
| Guide export | Reviewed instructions/media, annotations and provenance; working Markdown/HTML assets and hash-bound approval |
| Impact detection | PR/module/test changes resolve to affected sections; unmapped or new features produce coverage work |
| Deployment verification | Trusted receipt binds the application URL/environment to the expected head or merge/squash commit |
| Refresh | Same workflow recaptured through ContextQA; explicit before/after step mapping; reviewed scoped update |
| Reliable orchestration | Authenticated events, tenant scoping, durable deduplication/run ledger, bounded polling and ambiguous-start reconciliation |
| Delivery | Reviewed draft change in the configured destination; publication only under approved policy |

A generated test, request artifact, passing wrapper test or changed image hash does
not alone establish a verified documentation update. Record failed, missing and
unknown evidence without replacing the last approved guide with unsupported claims.

## What has been established

The [Kan receipt](verification-2026-10-30.md) records successful ContextQA
case 174/result 372 for login, board/list/card creation and persistence. The wrapper
implements review/export/compare utilities. The Kan request-only trigger has a hosted
CI receipt. These do not prove complete application coverage, an exact deployed SHA,
a PR-specific before/after refresh, automatic client-skill loading or publication.

The remaining product work is manifest validation, client-instruction management,
deployment verification, event orchestration, selective generation and draft delivery.
See [how to use](how-to-use.md#implementing-the-automated-product-layer).

## Optional destinations

- [Layerpath runbook](../examples/layerpath-lifecycle/README.md): proposed handoff of
  reviewed ContextQA assets into a tour-authoring workflow, subject to current account
  capabilities. No native project or automated adapter is verified.
- [EkLine runbook](../examples/ekline-lifecycle/README.md): proposed handoff of approved
  prose/assets/change context into a documentation editor, subject to current access.
  No native session, PR or automated adapter is verified.

For either destination, separately establish supported intake/update/export behavior,
scoped access and a real native draft/update receipt. Capture remains in ContextQA.
Verify destination navigation, asset rendering and sharing controls before publication.
Do not buy subscriptions, expand integrations or enable schedules merely to complete
an example. Historical vendor references need revalidation before implementation.

## Practical order

1. Maintain the verified core Kan guide and coverage gaps.
2. Complete one exact-revision capture → reviewed refresh → draft-change lifecycle.
3. Implement the event/manifest/instruction layer with failure and duplicate tests.
4. Add a destination adapter only for a client who needs it, with its own acceptance.

A client can use exported Markdown/HTML and repository review without either optional
platform. A generic browser-session service is not required for this documentation path.
