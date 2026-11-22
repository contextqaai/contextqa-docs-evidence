> **Policy update:** Product workflow evidence must come exclusively from ContextQA executions. Manual-browser captures are rejected by `guides build`. Use `journeys prepare --editorial-specs` with provenance-checked exports, then the [ContextQA writer library](contextqa-writer.md). The low-level compiler remains useful for offline renderer tests, but it cannot approve or promote documentation.

# Evidence-linked editorial guides

Use the editorial path when the deliverable is a how-to guide with explanations, prerequisites, checkpoints and captioned screenshots. The older journey step-list renderer remains available for compatibility; it is not the Learning Hub quality benchmark.

Use the structured spec in the ContextQA writer's reviewed output as the authoring reference. Renderer tests use explicitly synthetic fixtures. Earlier manual-browser layout research remains local and is excluded from delivery and acceptance.

## Build without an application

From the repository root:

```sh
python3 -m cqa_artifacts.guides build \
  --spec private/guide-spec.json \
  --evidence-root private/reviewed-contextqa-export \
  --out /tmp/new-editorial-guide
```

The build requires a real, passed, deployment-bound ContextQA export with artifact download provenance. The new directory contains `index.html`, `guide.md`, content-addressed image files and `quality-report.json`. No server, account, model key or remote request is required. Use an unused output directory to preserve previous evidence.

An author or agent supplies `editorial-guide-v1` JSON. The compiler requires audience, goal, summary, prerequisites, sources, figures and stable section IDs. Procedures require explanations, actions and an expected result. Each section identifies its sources and figures. Each figure requires its actual file SHA-256, pixel width/height, purpose, caption, alt text and explicit privacy/state/readability review flags. See `tests/fixtures/editorial-guide.json` for the structural schema; its evidence is synthetic and cannot be promoted.

These flags are reviewer attestations. They do not run OCR, inspect pixels, prove rights or certify factual truth. Missing execution and editorial reviews remain in the report. `publication_ready` is always false: compilation does not grant publishing approval. The HTML and Markdown escape supplied prose rather than execute HTML or MDX from an author/model.

## Use reviewed ContextQA journeys

The existing preparation path now accepts a mapping of affected article paths to editorial specs:

```sh
python3 -m cqa_artifacts.journeys prepare \
  --registry private/journeys.json --plan private/change-plan.json \
  --exports private/exports.json --editorial-specs private/editorial-specs.json \
  --out private/new-editorial-review
```

Each `contextqa-run` source names a `journey_id`. Each figure names that same `journey_id`, a reviewed export's `media_id`, a source ID and the exact screenshot SHA-256. The adapter fills execution fields from the validated export and resolves the image from that export. It rejects unmapped journeys, mismatched source/media associations, changed images and unknown article paths. Other source records may cite reviewed product references; they do not substitute for executed evidence.

Existing deployment, verdict, source revision and result-hierarchy checks still run before editorial drafting. The resulting proposal uses the existing `evidence/<export_digest>/...` media layout, Git patch and review database. Quality blockers become review questions. No paid model or execution starts implicitly.

The generated guide is enclosed in `contextqa:editorial:start/end` markers. Updates replace that block and preserve prose outside it. A malformed or duplicate block is rejected. Migrating an old step-list article requires a deliberate editorial change to avoid retaining redundant old blocks. This first version does not intelligently merge arbitrary prose inside the managed block.

## Detect documentation impact

```sh
python3 -m cqa_artifacts.guides impact \
  --before /tmp/previous-guide/quality-report.json \
  --after /tmp/new-editorial-guide/quality-report.json
```

The report identifies section content, source and figure changes, plus document metadata and section order changes. Unchanged inputs produce identical output and no changes. Source changes fan out only to sections that reference that source. Use fine-grained source records to avoid excessive fan-out.

This is dependency-aware digest comparison, not semantic visual comparison. A changed timestamp in a source record is still a change. The agent must interpret the impact, recapture the required UI states, author revised sections and submit a review. The command neither repairs tests nor publishes content automatically.

## Authoring instructions for an agent

1. Read the user goal, reference guides and the existing article. Choose a tutorial, concept or reference structure before writing.
2. Build a capture plan for specific visible states. Reuse saved ContextQA cases where possible and maintain their definitions through the existing journey workflow.
3. Verify the deployed version and the selected run. Do not turn failed, partial or historical runs into current successful behavior.
4. Inspect each selected image at publication size. Choose a useful crop, remove sensitive information through an approved deterministic processing step, and preserve provenance. Never generate replacement product UI.
5. Write explanations that answer why a setting matters, instructions with exact visible labels, expected outcomes and recovery paths. Cite authoritative references for behavior not established by execution.
6. Produce the structured spec. Keep stable section and figure IDs. Do not set review flags that have not actually been checked.
7. Compile, inspect the rendered page, compare against the previous report and use the existing review workflow. Test with a reader unfamiliar with the task.

## Acceptance boundaries

Implemented: structured authoring input; HTML/Markdown compilation; caption/alt/source requirements; hash-locked local screenshots; dependency impact; reviewed-journey integration; preserved surrounding prose; explicit evidence and editorial gaps.

Not implemented: autonomous guide planning/writing, automatic screenshot selection/redaction/vision checks, video transcription/chaptering, semantic image diffs, full claim-level truth validation, native GitBook publication, or a scheduled end-to-end maintenance service. See the ContextQA writer acceptance record for live execution scope; renderer tests do not establish learner acceptance.
