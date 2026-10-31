# Use ContextQA evidence to create and maintain documentation

This guide explains today's operator workflow and the proposed automated lifecycle.
ContextQA executes the application and supplies evidence; this repository collects,
reviews, annotates, exports and compares documentation. It does not currently offer
one-command URL crawl → complete handbook → automatic publication.

## What is available today?

| Capability | Status |
| --- | --- |
| ContextQA authoring, saved-plan execution and result adapter | Implemented against the token contract; transport tests are not universal tenant acceptance |
| Import selected results, attach reviewed media, annotate, export Markdown/HTML | Implemented; see CLI examples below |
| Compare reviewed before/after exports | Implemented with explicit step mapping; text/media hashes, not semantic interpretation |
| Kan PR changed paths → documentation capture request | Implemented and exercised in [Kan PR 19](https://github.com/nigharsh/kan/pull/19) |
| ContextQA crawl, test generation and optional repository/module discovery | Upstream onboarding input; this wrapper does not implement the crawl or a general module-sync connector |
| Client instruction template and section/test/module manifest | Examples provided; automatic loading, validation and enforcement are not implemented |
| Deployment-to-capture orchestration, selective regeneration and draft-PR writer | Proposed integration work, not activated by these examples |
| Native documentation hosting or automatic publication | Not implemented |

The [Kan receipt](verification-2026-10-30.md) records a real successful ContextQA
workflow (case 174/result 372). It proves login, board/list/card creation and a
persistence check, not every Kan feature or an exact deployed commit.

## 1. Onboard the application in ContextQA

Supply the application URL and authorized test access in ContextQA. Confirm the
tenant/workspace and environment before creating or running cases. Keep credentials
in ContextQA's approved auth/environment mechanism, never in this repository,
GitHub event payloads or documentation instructions.

Use ContextQA's onboarding/crawl/test-generation flow where supported by the tenant.
Optionally connect the source repository for upstream module and PR-impact analysis.
Read back the generated cases/modules; a queued generation job or empty response is
not completed coverage. Review scope, roles, isolated data and destructive/external
actions before execution. Generated tests propose documentation topics; execution
supplies verified instructions and media. Do not substitute a local browser runner.

Without a repository, group documentation by workflow and use explicit/manual or
release events for recapture. Do not claim code-level impact precision without a
code-to-workflow mapping. Authentication modes, roles and tenants can expose
materially different workflows; document their scope separately.

## 2. Define client instructions and the documentation outline

Copy [DOCUMENTATION_STYLE.md](../examples/documentation-lifecycle/DOCUMENTATION_STYLE.md)
into the client's controlled configuration. Set audience, terminology, brand rules,
page structure, screenshots, privacy exclusions and approval policy. Have the owner
review it and record its content hash with each generation job. Treat instructions
from unapproved PR branches as proposed changes, not trusted execution policy.

The template is a project instruction document. It is **not** an installed ContextQA
skill and is not automatically read by this CLI or the optional AI script. Today an
operator follows it during drafting and review. Automatic skill/profile ingestion,
version binding, compliance checks and theme configuration require implementation.
No `--skill` or `--brand` flag is implied.

Start with an outline: getting started, primary tasks, feature reference,
administration and troubleshooting. Assign stable section IDs, owners, workflow
IDs and supporting test IDs. Add module IDs/code paths if available. The
[manifest example](../examples/documentation-lifecycle/manifest.example.json) is a
proposed storage contract, not a loadable CLI profile. Its null IDs are placeholders;
never submit them to a live API. The existing execution profile has a different
schema described in [platform configuration](contextqa-platform.md).

## 3. Execute and collect a baseline

Run selected cases/plans in ContextQA against the intended environment, with the
required capture settings. Record the accepted run ID once and poll that run; do not
retry an ambiguous start. Account-specific execution/cost authorization must already
cover the selected run. A full example for the existing saved-plan CLI is in
[ContextQA API usage](contextqa-api.md#start-once-then-poll-the-accepted-run).

Record the actual mode; do not rename EXPERT as Max. Bind evidence to a deployment
receipt containing application URL, environment and full commit SHA where available.
For post-merge validation, that SHA may be the merge/squash commit rather than the PR
head: explicitly retain the relationship. An arbitrary supplied SHA or successful
build status does not prove the shared application URL serves that revision.

Install from the reviewed checkout using Python 3.10+:

```sh
python3 -m pip install .
python3 -m cqa_artifacts --help
python3 -m cqa_artifacts init workspaces/release-a --title 'Create a card'
```

For the token adapter, inject `CONTEXTQA_API_TOKEN` through your approved secret
manager and select the actual plan-run/case-result/step-result hierarchy:

```sh
# Replace the identifiers with verified integers before running.
python3 -m cqa_artifacts contextqa-collect workspaces/release-a \
  --run-id PLAN_RUN_ID --case-result-id CASE_RESULT_ID \
  --step-result-id STEP_RESULT_ID --import-steps
```

Use an empty workspace when importing steps. `PLAN_RUN_ID` is not interchangeable
with a case result ID: do not put Kan case result 372 into `--run-id` merely because
it is a run-result page. The Kan proof was collected through MCP; automatic MCP-to-
wrapper import is not established. For MCP-only case evidence, inspect the returned
record privately and author steps/media explicitly through the supported CLI, keeping
provider references and membership evidence. Do not claim token-adapter acceptance
from an MCP execution.

Terminal success and per-step evidence are required for a verified happy-path guide.
Keep failure/partial/zero-executed results as troubleshooting evidence or blockers.
A single passing AI step is not a separate passed result for every generated action.

## 4. Draft, attach media, and annotate

Create concise task steps using observed labels and expected results. Use the client
instructions during authoring. For an explicit manually reviewed step:

```sh
python3 -m cqa_artifacts add-step workspaces/release-a \
  --title 'Create the card' --instruction 'Enter a meaningful title, then select Create card.'
python3 -m cqa_artifacts add-media workspaces/release-a \
  --kind screenshot --file /absolute/path/to/reviewed-contextqa-frame.jpg
# Substitute the actual returned media ID and selected step number.
python3 -m cqa_artifacts attach workspaces/release-a --step 1 --media-id MEDIA_ID
```

For selected remote references use `fetch-media` with the exact reviewed storage
host as described in [capture documentation](documentation-proof.md). Do not forward
API credentials to storage. A trace frame is an image from ContextQA execution, not
a manually captured browser screenshot. Review pixels; filtering text is insufficient.

Use `capture-context` for revision/time/mode labels and `annotate` for percentage-based
rectangles. Both use reviewed JSON files; see [formats](documentation-proof.md).
Labels alone do not attest the application version. Retain the source execution and
selected-frame provenance outside public output. Never export raw traces, credentials,
unreviewed recordings or expiring signed URLs as public documentation.

The optional [AI drafting helper](ai.md) accepts reviewed text with explicit sharing
approval. It does not load the client instruction template, execute workflows,
approve evidence, or apply generated changes automatically.

## 5. Review and export

Inspect every selected instruction, frame and recording for accuracy, identifiers,
rights and compliance with the client's guide. Approve only the reviewed content:

```sh
python3 -m cqa_artifacts inspect workspaces/release-a
python3 -m cqa_artifacts approve workspaces/release-a \
  --reviewer 'Documentation owner' --confirm-rights-and-reviewed-content
python3 -m cqa_artifacts export workspaces/release-a \
  --out exports/release-a --base-url https://docs.example.com/create-card
```

The URL is an example export label; export does not host or publish anything. Preserve
relative image assets when moving Markdown or HTML. Approval is hash-bound; edits to
text, metadata, annotations or media require review again. Client branding does not
turn unverified content into verified content.

## 6. Refresh after a change

See [trigger recipes](documentation-triggers.md). First determine affected sections;
then wait for a verified deployment and run the relevant ContextQA workflows. Create
a separate reviewed export rather than overwriting the baseline. Explicitly map every
old/new step using [the change-context example](../examples/change-context.json):

```sh
python3 -m cqa_artifacts compare exports/release-a \
  --after exports/release-b --context private/change-context.json \
  --out exports/change-review
```

Review the proposed update with old/new instructions and screenshots side by side.
Changed screenshot hashes alone do not prove a meaningful product change. Preserve
handwritten sections and unchanged evidence. New features need new sections and
coverage; removed features need an explicit retirement decision; unmapped changed
modules require review rather than silently declaring nothing affected.

An approved brand-only change can redraft existing reviewed content without another
application run when its behavior/revision applicability is unchanged. Record the
new instructions hash and review again. Behavior changes need new execution evidence.

## Implementing the automated product layer

1. Add a validated, tenant-scoped manifest for section ↔ workflow ↔ test ↔ module
   relationships, owners, baseline exports and approved instruction versions.
2. Consume upstream onboarding/test-generation results and propose the outline.
3. Normalize upstream PR-impact events into affected sections; preserve unknown and
   uncovered areas, deleted features, generated-test status and full revision identity.
4. Build an authenticated event receiver/queue with deduplication and a durable
   execution ledger. Gate capture on deployment and approved run policy.
5. Collect real evidence, selectively generate sections under the approved client
   instructions, and enforce privacy/brand/coverage checks before review.
6. Create a draft docs change with provenance, then publish only through the configured
   owner-approved destination. Publishing adapters and automatic policies are separate.

These are extension points, not endpoints or commands currently shipped by this repo.
Keep the existing renderer and ContextQA execution ownership; do not add a second crawler.
