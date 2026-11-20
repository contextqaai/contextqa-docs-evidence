# Saved journeys → evidence → documentation

The agent runs as a Python CLI in a developer checkout or CI job. No application server, React build, PostgreSQL or scheduler is needed. ContextQA remains the owner of saved cases, typed steps, prerequisites, environments, plans and executions. Git holds the journey-to-source/documentation mappings and expected definition hashes. Local private directories hold captures and immutable review receipts.

## What the loop does

1. `agent plan` compares immutable source commits and maps affected articles. It reads article baselines at the head commit so it preserves documentation already edited in the product PR.
2. `journeys impact` selects saved journeys by section and code-path mappings. Missing coverage is explicit; `prepare` refuses to use incomplete mappings.
3. `register` adopts existing ContextQA cases and snapshots every selected case's steps. Stable definition hashes detect changed actions, selectors, test data or ordering without committing their private contents. Include prerequisite cases in the profile so their definitions are checked too. Expiring golden-screenshot query signatures are excluded from definition hashes; the underlying artifact path is retained.
4. `maintenance-plan` prepares reviewed changes to registered cases/steps. `apply-maintenance` rechecks definition drift, journals each write, verifies its result and writes `registry.next.json`. It never deletes or replaces a case with an opaque AI test. Test updates require a reviewed proposal; code changes are not assumed to imply a safe selector/assertion rewrite.
5. `run` executes an explicitly approved saved plan once, records its accepted ID, and polls for a bounded interval. `capture`/`collect` can instead consume existing run IDs without starting anything. Selection validates plan→case→step identity and complete step counts; it never substitutes an unrelated latest passing run.
6. `media` retrieves screenshots/videos from explicitly selected storage hosts into private files and proposes step associations. A case recording is associated with that case's first documented step. Downloads remain unapproved.
7. `review` binds reviewed audience instructions and selected media to exact result IDs and a verified deployment attestation. Required media, successful execution and matching revision are mandatory. The resulting export omits raw responses, credentials and signed URLs.
8. `prepare` refreshes managed journey blocks in existing documents, copies approved media for local preview, creates a patch and attaches evidence to the local review database. It preserves prose outside the managed blocks. Every affected journey must be represented; one capture cannot satisfy unrelated journeys.
9. Normal CLI review decisions and approval produce a bundle. The draft-PR adapter can commit the reviewed Markdown/MDX and content-addressed screenshot/video assets together. It does not merge or publish the site.

The deterministic draft uses reviewed instructions and media; it does not infer what a video shows. Record relevant timestamps/observations in the review recipe after inspecting the recording. The optional BYOK drafting script can synthesize the source diff with the reviewed evidence text and media links; it does not send raw video to a model or claim automatic video transcription.

## Files and registration

See `examples/kan-pr15/journeys.json` for a registry adopted from live saved cases. That example deliberately maps only established card-creation coverage; rename and API documentation remain unmapped. Its historical capture is not a passing acceptance fixture.

A journey specifies a stable ID, documentation section IDs, source path patterns, target URL/environment, workspace version, case IDs, required media (`screenshot`, `video`) and a ContextQA profile. The profile contains an expected plan and case configuration. It may also include prerequisite cases, suites and steps. Never put credentials or literal login test data in a committed registry. Adopt existing tests with:

```sh
python3 -m cqa_artifacts.journeys register \
  --registry .docs-journeys.seed.json --journey create-card \
  --out .docs-journeys.json
```

This reads ContextQA; it does not create remote objects. Author new cases/steps/plans through ContextQA's native tools or the existing contract-derived authoring adapter, then register their real IDs. Do not use fictional IDs or guessed action/locator formats in a live registry.

## A developer refresh

From the agent repository, after injecting `CONTEXTQA_API_TOKEN` through your secret manager:

```sh
python3 -m cqa_artifacts.agent plan \
  --repo /absolute/product-checkout --config /absolute/product-checkout/.docs-agent.json \
  --base FULL_BASE_SHA --head FULL_HEAD_SHA --out /private/new-change/plan.json
python3 -m cqa_artifacts.journeys impact \
  --registry /absolute/product-checkout/.docs-journeys.json \
  --plan /private/new-change/plan.json --out /private/new-change/impact.json
python3 -m cqa_artifacts.journeys collect \
  --registry /absolute/product-checkout/.docs-journeys.json \
  --plan /private/new-change/plan.json --runs /private/run-map.json \
  --out /private/new-change/captures
```

`run-map.json` maps every impacted journey ID to `{ "run_id": ACCEPTED_RUN_ID, "deployment": ATTESTATION }`. This reads existing runs. No paid execution is hidden in collection or preparation. Each capture records failed/inconclusive outcomes rather than silently dropping them. Partial collection has receipts for completed journeys and must not be mistaken for a complete refresh; do not replay a run trigger to recover a collection failure.

A deployment attestation has the exact fields below. Obtain it from your deployment/CI records and review it. This is an operator attestation, not a cryptographic deployment signature or a version guessed from the target URL:

```json
{
  "run_id": 123,
  "commit_sha": "FULL_40_CHARACTER_COMMIT_SHA",
  "application_url": "https://qa.example.com",
  "environment": "QA",
  "journey_digest": "HASH_OF_THE_REGISTERED_JOURNEY",
  "verified_by": "deployment reviewer or CI identity",
  "evidence_ref": "deployment record binding this run and test definition to this commit",
  "confirmed": true
}
```

`journey_digest` is `cqa_artifacts.loop.fingerprint(registry['journeys'][N])`. It binds the definition version as well as the source revision. A capture without an attestation remains inspectable but cannot enter the evidence-backed documentation path.

```sh
python3 -m cqa_artifacts.journeys media \
  --capture /private/new-change/captures/create-card \
  --allow-host YOUR_REVIEWED_STORAGE_HOST --max-files 20
# Inspect each image/recording and edit review-recipe.json into useful instructions.
python3 -m cqa_artifacts.journeys review \
  --capture /private/new-change/captures/create-card \
  --recipe /private/new-change/captures/create-card/review-recipe.json \
  --reviewer 'Editor name' --confirm-content-and-rights \
  --out /private/new-change/reviewed/create-card
```

The recipe contains a `steps` array in collected order. Each entry supplies `step_result_id`, `title`, `instruction`, and `media_ids`. Include observed video timestamps in the instruction when useful. Every step must be reviewed. The export requires all journey media kinds. Use the lower-level `fetch-media` command for individually selected artifacts or additional downloads; it never forwards the API token to storage.

Create `exports.json` mapping each journey ID to its absolute reviewed export directory, then:

```sh
python3 -m cqa_artifacts.journeys prepare \
  --registry /absolute/product-checkout/.docs-journeys.json \
  --plan /private/new-change/plan.json --exports /private/new-change/exports.json \
  --out /private/new-change/docs-review
```

For model-assisted editing, first run `journeys evidence-plan` with the same registry/plan/exports arguments and a new `--out`. Pass that enriched plan to `scripts/docs-agent-draft.js` with explicit provider data-sharing approval, then supply the resulting `--proposal` to `journeys prepare`. No model call is required for deterministic managed-block updates.

Review with `cqa-docs-loop --db .../review.db --project PROJECT state`, decide each article, answer remaining questions and explicitly approve content/rights. `bundle` exports the approved package; `draft-pr` requires a clean target revision and explicit delivery confirmation. Bundles currently limit embedded evidence to 16 MiB; use smaller reviewed recordings or a separately reviewed media-hosting workflow for larger recordings. A draft patch alone excludes binary assets; use `drafts/` for preview or the approved bundle/draft-PR path for media delivery.

## Maintaining an existing journey

A private changes file is a list such as:

```json
[
  {"kind":"step","id":123,"changes":{"action":"EXACT_REVIEWED_ACTION"},"reason":"Product behavior changed; preserve and review the associated event/locator/test-data fields"}
]
```

This illustrates the envelope, not a valid tenant action. Preserve typed NLP fields from the actual case and update all relevant fields consistently. Never relax an assertion merely to make a run pass.

```sh
python3 -m cqa_artifacts.journeys maintenance-plan \
  --registry .docs-journeys.json --journey create-card \
  --changes /private/changes.json --out /private/maintenance.json
# Review the complete payload and its rationale before this write:
python3 -m cqa_artifacts.journeys apply-maintenance \
  --registry .docs-journeys.json --maintenance /private/maintenance.json \
  --approve-write --out /private/new-maintenance-receipts
```

Review and commit `registry.next.json` as the new registry. Existing captures become stale because their definition/registry hashes differ. The API has no conditional PUT in the inspected contract: use a controlled authoring window. Ambiguous writes leave receipts and are never automatically replayed. Schema projection preserves writable non-null fields and omits unset null fields rejected by the write schema.

For a new authorized execution, `journeys run --registry ... --journey ... --out NEW_DIRECTORY --approve-execution` performs a preflight, one saved-plan start and bounded polling. Execution approval covers the entire saved plan, not only the mapped cases selected for documentation. The existing profile may configure prerequisites, data iterations and retries; inspect that scope and applicable cost before approval. A polling timeout is not cancellation; continue reading the accepted run ID. There is no token-API stop operation.

## CI and limits

The composite action accepts `journeys` and optional `evidence-exports` inputs. It emits journey impact, enriches optional AI drafting with reviewed evidence, and prepares local review files. The product workflow must supply deployed revision/run receipts and approved exports. Do not run provider or ContextQA secrets on untrusted fork code. Upload only the selected review artifacts appropriate to the repository audience, never an entire private capture directory.

Tests cover transport simulation and negative paths, not live browser correctness. The real Kan acceptance receipt separately records current API reads, failed historical outcomes, missing coverage and deployment blockers. No PageLoop parity or production execution claim follows from a passing local suite.
