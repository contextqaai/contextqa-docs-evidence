# ContextQA documentation writer

Use this workflow when asked to create or maintain product documentation. The user's product target, scope and execution authorization govern the work. No separate browser operator may supply product evidence.

## Persistent inputs

Keep a repository manifest, a saved-journey registry, an editorial spec per article, and a documentation library. Case/plan IDs and definition hashes belong in Git; account variables stay in ContextQA. Configure documentation-only cases with stable sample data, screenshots at useful states and recordings. Bound runs and retries; never rerun an ambiguous accepted start.

## Starting with only a URL, credentials and goal

Existing saved journeys are not a prerequisite. Bind the authorized credentials to a dedicated ContextQA environment and create an AI bootstrap case from the user's goal. The prompt must name the target, scope, assertions, evidence checkpoints and test-owned data policy. Execute through ContextQA; inspect the actual result and generated typed steps. Use these captured locators to maintain reusable cases. Never replace a previously authored typed case with an opaque AI step to hide failures.

Split broad coverage into independently diagnosable journeys. Distinguish authored, accepted/queued, executed, passed, failed and unavailable workflows. Persist accepted execution handles; a startup delay is not permission to retry the start. Keep an explicit coverage matrix and cleanup outcomes. Do not claim exhaustive testing from a generic navigation pass.

A public application URL does not prove a deployed commit. Without source/deployment identity, retain the run evidence and draft documentation with that limitation; do not invent a revision to satisfy the latest-copy deployment gate.

## Work autonomously through these stages

1. Read the changed source and existing guide. Identify user-visible changes and select affected journeys. Preserve independent explanations and product-reference facts.
2. Inspect saved cases using ContextQA MCP/API. Maintain their typed steps and assertions as required, using captured ContextQA locators or a ContextQA AI bootstrap. Never use browser recon outside ContextQA, fabricate selectors, or weaken assertions.
3. Register the maintained case definitions. Start the scoped ContextQA plan, retain the accepted run ID, and poll its actual terminal verdict. The saved plan's whole suite/device matrix is the execution scope.
4. Bind the run to the deployed revision using verified deployment metadata or an explicit user attestation labeled as such. Do not substitute a latest Git SHA for deployment verification.
5. Run `docs-writer collect` with the accepted run map and exact allowed media hosts. A failure leaves latest untouched. Read `authoring-brief.json` and inspect only the downloaded ContextQA images/videos. Missing evidence requires another appropriate ContextQA capture, not a substitute screenshot.
6. Draft complete user-facing instructions: goal, prerequisites, choices, actions, checkpoints, troubleshooting and related material. Select useful images with meaningful captions and alt text. Explain recordings only after inspecting them; preserve exact timestamps for observations. Do not expose credentials or signed URLs.
7. Write the reviewed per-step recipes and editorial specs. Cite every figure's journey/media ID and byte hash. Inspect readability at publication size, privacy and text/image agreement. Never mark an independent task-completion check passed without a recorded independent execution or reader check.
8. Run `docs-writer finalize` after actually reviewing the content and rights. Outstanding quality questions block advancement. This creates the review package and calls the immutable library update. No app server is needed.
9. Show the resulting guide, the before/after comparison, ContextQA run IDs and latest-copy location. Distinguish a fixture/content change from a product release. Do not claim semantic visual analysis from a hash diff.

## Refresh

Repeat with the same registry after the next change. Use `collect --library` to take the current approved local article as the baseline, then finalize with the exact `latest.json` version hash. Do not silently overwrite newer versions. Same inputs must not create duplicate executions; collect/finalize never trigger tests. A failed run, missing media, stale definition or unresolved quality issue cannot replace the approved copy.

## Acceptance

Show two ContextQA-produced captures for a maintained journey, a useful generated guide, an inspectable before/after report and an unchanged latest pointer for a deliberate invalid candidate. Offline fixtures must be labeled tests. A passing unit suite is not live acceptance.
