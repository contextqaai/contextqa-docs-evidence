# ContextQA as the documentation operator

ContextQA owns the durable user journeys and performs the product activities. The documentation coordinator consumes ContextQA execution evidence, writes guides, compares versions and maintains the latest approved local copy. A separate browser driver is not an alternative evidence producer.

## URL, credentials and goal are enough to start

The coding agent can create initial saved journeys through ContextQA's AI bootstrap, using `create_test_case(task_description=..., environment_id=...)`, then execute them to obtain typed steps and actual evidence. Pre-existing saved cases are not required. See [OrangeHRM prompts and setup](../examples/orangehrm/README.md) for a scoped example. Credentials stay in ContextQA environment variables.

This bootstrap is an agent/MCP workflow, not an implicit paid action inside `docs-writer collect`. Collection accepts existing run IDs so resumes cannot accidentally create duplicate executions. Bootstrap acceptance and execution success are separate states. Documentation promotion still requires the evidence, review and deployment gates below.

## Operating loop

1. Map a documentation topic to saved ContextQA cases, a plan, fixture/environment configuration and required capture checkpoints. Preserve the cases in ContextQA so the next change reuses or deliberately maintains the same journey.
2. Review the change against the existing case definitions. Update the affected typed steps and assertions through ContextQA, then register the new definition hashes. Do not relax assertions to make an obsolete guide pass.
3. Execute the approved ContextQA plan against the matching deployed revision. Retain the accepted run ID; never retry an ambiguous start.
4. Collect the run/case/step hierarchy and download the available screenshots/recordings from those results. Every selected media item must have a retrieval receipt associating it with the documented step or case. Manual browser screenshots cannot be substituted.
5. Review those actual images and recordings. Use the editorial guide specification for prerequisites, explanations, actions, expected outcomes, captions and troubleshooting. Product reference sources may explain concepts, but cannot serve as substitute workflow screenshots.
6. Prepare and review the documentation changes. Keep the current guide unchanged while candidate execution/evidence is incomplete or failed.
7. Promote the approved result into an immutable local version. Compare text and evidence before/after; advance the latest pointer only after the complete version is written.

See [journey commands](journey-agent.md) and [editorial specs](editorial-guides.md). The coordinator is a CLI/library; no review application is required.

## Resumable agent workflow

Use `agent-instructions/contextqa-writer.md` as the coding agent's operating instructions. The agent reviews the source change, maintains the saved ContextQA journey, and writes the editorial specification after inspecting ContextQA evidence. No separate application is needed.

```sh
docs-writer collect --plan private/plan.json --registry private/journeys.json \
  --runs private/runs.json --out private/refresh \
  --allow-host REVIEWED_ARTIFACT_HOST --library private/documentation-library
```

`runs.json` maps each affected journey ID to `{ "run_id": 123, "deployment": {...} }`. Use the deployment attestation fields in the journey guide. Collection never starts tests. It resumes the same inputs, preserves failed captures, and produces `authoring-brief.json` with local evidence paths. Inspect all selected media, then author complete guides and review recipes. A changed source, registry or run map needs a new workspace.

```sh
docs-writer finalize --workspace private/refresh \
  --recipes private/reviewed-recipes.json --editorial-specs private/editorial-specs.json \
  --reviewer 'Reviewer identity' --library private/documentation-library \
  --expected-latest none --confirm-content-and-rights
```

Recipes map journey IDs to reviewed recipes; editorial specs map article paths to guide specifications. Finalization blocks incomplete quality checks, reviews validated evidence, and promotes the approved copy. This flag records the operator's actual review; it does not perform visual review or independently follow the instructions. A blocked editorial specification may be corrected and resumed without executing another test. Completed inputs are immutable. CLI commands reject simulated evidence for promotion.

## Current copy and history

After approving the prepared review using the existing review workflow:

```sh
python3 -m cqa_artifacts.library \
  --review private/prepared-review \
  --registry private/journeys.json \
  --exports private/exports.json \
  --library private/documentation-library \
  --expected-latest none
```

Use `none` only for the first adoption. Subsequent updates supply the exact current version hash from `latest.json`. This guards against replacing a newer copy using an older baseline.

The library contains:

- `latest.json`: points to the complete current approved documentation tree.
- `versions/<hash>/files/`: Markdown/MDX, readable `.md.html` previews and bundled ContextQA evidence.
- `versions/<hash>/version.json`: source revision, journey/run IDs, parent version and file hashes.
- `versions/<hash>/changes.diff`: before/after documentation text.
- `versions/<hash>/changes.json`: media identity changes.
- `versions/<hash>/comparison.html`: before/after document text plus historical/current image and recording links.

An identical approved replay does not create another version. A lock prevents simultaneous promotion; a crashed operation leaves a lock for explicit reconciliation. Validate a leftover version before removing a stale lock. The pointer is replaced only after the version is complete. Existing versions are not edited. No remote publication or GitHub push occurs.

The comparison reports text and media identity, not semantic visual differences. Old media remains available for historical references. Sensitive original recordings still require review; the existing reviewed bundle limit is 16 MiB.

## Provenance checks and migration

`journeys review` now requires selected images/videos to match the private download receipt and a ContextQA result artifact associated with that step/case. `journeys prepare` requires `contextqa-only-v1` receipts. Legacy exports need a new review with their original retrieval records; assigning a source label to a manual screenshot does not make it ContextQA evidence.

The historical manually captured Test Plans example is excluded. It remains available only to inspect the intended editorial layout. It is not an accepted guide, a live test execution, or a latest verified version.

## Recording frames when screenshots are unavailable

Use `docs-writer collect --recording-frames` when ContextQA's recording downloads work but its screenshot references do not. This requires `ffmpeg` on the operator machine. It extracts unchanged PNG frames from ContextQA step recording intervals. Each frame retains the source recording hash, ContextQA artifact receipt, step result ID and millisecond timestamp. Review decodes the same frame again and checks its hash. No separate browser or generated UI image is used. Caption these images as frames from the ContextQA recording. Multiple ambiguous recordings or missing step timestamps stop extraction.

Captures are private until selected and reviewed: sign-in frames and recordings may contain personal data. Only attach the media that is appropriate for the intended audience. Original recordings are retained; the tool does not claim automated video redaction.

ContextQA may add screenshot references or metadata after a run. Diagnostic screenshot changes on non-visual steps are excluded from definition locks; visual assertion baselines remain locked. Other definition mismatches stop collection; inspect and reconcile them before registering the next version. Do not simply disable definition locks.

## Remaining work

These commands implement provenance enforcement, review integration, immutable versions, before/after presentation and latest-copy management. They do not yet implement autonomous technical-writing judgment, video transcription, semantic visual comparison, automatic change-triggered execution policies or native GitBook publication. No claim of a fully autonomous ContextQA documentation writer follows from local test success. The [live acceptance record](contextqa-writer-acceptance.md) documents two passed executions of the maintained Kan journey, user-attested deployment binding, reviewed recording frames, immutable versions and rejection of altered evidence.
