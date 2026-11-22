# M14 — Media editing and recording-assisted intake

Status: planned; phase: Parity. Dependencies: M06,M08.

## User outcome

A writer can make evidence images legible and explain a recording without compromising provenance.

## Existing foundation

`frames.py; guide figures; transcript_event`

## Scope and workflow

Media drawer, crop/redact/annotate, image comparison, caption/alt, recording segmentation, narration/transcript mapping and missing-capture requests. ContextQA produces workflow-proof captures; uploaded recordings are supplemental reference material unless verified by an approved ContextQA journey.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

ArtifactOriginal, ArtifactDerivative, TransformRecipe, TranscriptSegment, CaptureRequest; immutable parent checksum and role/environment/checkpoint links.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M14-T01:** Build evidence media browser and exact placement in article.
- **M14-T02:** Add deterministic crop/redaction/annotation with parent/derivative lineage.
- **M14-T03:** Add recording segments and selected-frame verification against source recording.
- **M14-T04:** Add retake/missing-media flow routed through ContextQA saved journeys.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Saved image points to immutable original and transformation recipe.
- AC-2: Redaction obscures exported pixels; original is not exposed through public derivatives.
- AC-3: Wrong-role/wrong-screen image fails review despite successful capture.
- AC-4: Upload/capture/placement/review/publication each has a distinct state.
- AC-5: Missing image retains blocker; no generated product UI replaces it.

## ContextQA journey and reader guide

**Redact a captured screenshot and place it in a guide.** As a media editor, select a verified frame, redact a synthetic marker, place the derivative beside the matching instruction and preview it as the reader. Capture the placement and verify the exported pixels.

**Negative and recovery coverage.** Select a wrong-role frame or remove the required asset. Verify the blocker, replace the frame and ensure the reader only receives the approved derivative.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deliberate deviation: do not implement a separate Chrome recorder as a workflow-proof producer. Consider an intake helper only if it routes to ContextQA.
