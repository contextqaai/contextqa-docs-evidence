# ContextQA-only writer acceptance — 2026-11-20

The CLI and coding-agent workflow were exercised against Kan QA using saved ContextQA case **186**, suite **39** and plan **39** in Ship 5. No separate browser performed the product journey or supplied its evidence.

| Plan run | Case result | Outcome | Meaning |
| --- | --- | --- | --- |
| 45 | recorded in private capture | Failed | Full long board title was visually truncated. Retained; never approved. |
| 46 | 443 | Failed, 5/6 steps passed | Creation click occurred while the dashboard was loading. Retained; never approved. |
| 48 | 445 | Passed, 18/18 steps | `Docs Guide A`: board, list and card creation, with outcome assertions. |
| 50 | 447 | Passed, 18/18 steps | Same maintained journey using `Docs Guide B`; repeated task completion and refreshed evidence. |

[Saved plan](https://ship-5.contextqa.com/td/1/plans/39/overview) · [First passed case execution](https://ship-5.contextqa.com/run-result-view?testCaseId=186&runResultId=445) · [Repeat passed case execution](https://ship-5.contextqa.com/run-result-view?testCaseId=186&runResultId=447)

The target was `https://kan-qa.vercel.app`. The user attested that it contains PR 15 head `de9eb589ade097555b573473f9c833192d9af5a2`. This is explicitly recorded as user deployment attestation, not independently verified hosting metadata.

## Documentation and evidence

The guide explains prerequisites, the board/list/card hierarchy, three creation procedures, expected outcomes and how to identify the correct dialog. Four captioned images show the relevant states. It includes a link to the original ContextQA walkthrough recording.

ContextQA's screenshot references returned storage errors (unsigned references and incorrectly formed signed paths). Its recording downloaded successfully. The four images therefore are **unchanged frames extracted from the ContextQA recording**, not separate screenshots. Each has the recording hash, ContextQA artifact receipt, step result ID and timestamp. Review re-decodes the frame and checks its bytes. The original recording remains in the evidence package.

The recording is 800 × 450. This is the available ContextQA recording resolution, not a claim of full-resolution browser screenshots. The local guide preserves the image dimensions and legible captions. Media stays private because the recording includes the QA account identity; no credentials, signed storage URLs or recordings are committed here.

## What the acceptance establishes

- The agent maintains a persistent saved ContextQA journey through API writes, retains failed runs and reuses the same case/plan.
- Passed, deployment-bound evidence produces a task-based guide with images and a recording.
- Reviewed versions preserve the prior documentation and evidence, show before/after guides and text changes, and move the latest pointer only after a complete version is written.
- A deliberately altered figure hash is rejected with the latest pointer unchanged.
- Collection does not execute another test; completed finalization is idempotent. Offline regression tests cover missing provenance, stale definitions, failed/inflight runs, wrong frame timestamps, changed media and concurrent/latest-version protection.

The A → B difference is a **fixture/documentation refresh**, not a before/after product-release claim. Both runs target the same source revision. Repeated ContextQA task execution validates the procedure; it is not an independent human learner study. The agent still supplies editorial and visual judgment. Semantic interpretation of image differences, video narration/redaction and native hosted documentation publication are not implemented by the coordinator.
