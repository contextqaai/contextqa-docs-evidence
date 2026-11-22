# Software factory handoff

## How to use the existing factory

Keep its spec → independent test → implement → verify → review loop. Use this package as product input. The pasted payments-demo instructions are reference material: do not install its tools, clone its repo, use its demo credentials, start its billable runs, apply its five backlog items, or assume its 2.5-hour/credit figures apply here.

Use `BACKLOG.csv` as the module ticket queue. A ticket's spec must include goal, observed baseline, relevant requirement IDs, UX states, exact affected contracts, exclusions, acceptance checks and dependencies. Split any ticket that cannot be reviewed as one behavior change. Module docs do not authorize publishing, paid provider execution or merging merely by existing.

Suggested factory statuses: todo, ready, implementing, awaiting_test, failed, needs_input, reviewing, accepted. A ticket is accepted only after its specific behavior and necessary integration checks pass. “Code generated” and “tests authored” are intermediate states.

The [M00 receipt](m00-implementation.md) covers FND-01 through FND-04. The [M01/M02 implementation receipt](m01-m02-results.md) covers the onboarding and source intake work that followed. The [M03 acceptance report](m03-results.md) records existing-document import and inventory coverage.

## First implementation batch

### FND-01 — establish baseline and preserve work

Parent: M00-T01. Read AGENTS.md and this plan; inspect branch and dirty state. Preserve pre-existing CI edits/untracked examples. Record exact HEAD, changed files and current check results. Run existing Python, UI, AI transport, React and build checks; real Postgres tests if configured. Report environmental blockers distinctly. No paid model/capture calls for baseline checks. Done: repeatable check receipt and a concrete list of current failures, without changing unrelated code.

### FND-02 — screen/state audit

Parent: M00-T01. Inventory current components against ux-spec.md; for each screen mark wired/partial/missing, roles, data source and recovery behavior. Identify misleading “up to date” or “delivered” states. Done: every existing route mapped to real API behavior and one prioritized discrepancy list. Read source first; use ContextQA if runtime journey verification is needed.

### FND-03 — navigation and app shell

Parent: M00-T02. Extract reusable shell/navigation/tokens while preserving current review actions. Done: selected workspace and route persist; keyboard menu/focus works; 1440/1024/390 layouts are usable; existing review tests pass. No new navigation link should imply an implemented module: label planned areas or omit them.

### FND-04 — first-use and failure states

Parent: M00-T03/T04. Build Home from actual workspace state and show the next actionable setup/review step. Distinguish loading/empty/error/stale. Done: missing source leads to setup, no requests leads to create-guide, blocked review links to exact blocker, a failed fetch offers retry, and no fabricated metrics appear.

### FND-05 — onboarding service contract

Parent: M01-T02. Define persisted setup state and resume behavior against existing workspace/membership schema; implement the first bounded setup path. Done: refresh resumes, duplicate submit returns same created object, forbidden role changes fail server-side. Connector success remains incomplete until scope is configured.

## Template prompt for one module

```text
Implement only MODULE_ID in docs/continuous-documentation/modules/.
Read AGENTS.md, baseline-audit.md, product-spec.md, ux-spec.md and architecture.md.
Inspect the existing implementation before choosing edits; preserve unrelated work.
Convert the next ready ticket into a small spec with selected module AC IDs.
Reuse current domain/evidence code and keep ContextQA as the product-journey provider.
Implement actual API/data/UI behavior including failures and permissions.
Read feature-verification.md and the module’s example journey. For each shipped feature,
name the reader task and capture checkpoints. Map rules, negative/recovery, end-to-end,
design and UX assertions to evidence. Compare the result to the approved guide.
Record a create/update/retire/no-change/investigate decision and its review state.
Run relevant local checks. Use ContextQA acceptance only with the required target,
environment and bounded execution authorization. Never treat mocked providers as live proof.
Record exact build, tests, screenshots/evidence receipts, skipped checks and remaining gaps.
Update BACKLOG.csv. Stop at a reviewable change; do not claim the module complete
until all its ACs have evidence. Do not push, merge or deploy unless authorized.
```

## Test strategy adaptation

The demo's cap of four accepted tests was appropriate to small sample stories; it is not enough for these modules. Map tests to all applicable ACs, including permissions, conflicts, restart/idempotency and recovery. ContextQA owns application journey execution. Local unit, contract and PostgreSQL tests check deterministic domain/infrastructure behavior. An independent reviewer in the user's configured factory should evaluate code against the spec; this planning task does not launch that factory or subagents.

Do not let a builder rewrite a failing acceptance test simply to make it pass. If test intent is wrong, retain the original failure, document the discrepancy, have the spec/test owner approve the correction, and replay it. Generated journey bootstrap and saved-action replay are different checks.

## Standard receipt

Record ticket/module/AC IDs; base and candidate commit; target URL and deployed revision evidence; test case and execution IDs; result and covered assertions; original failures; media source; reviewer decision; blocked checks; next ticket. No secrets, private recordings or signed URLs in committed receipts.

The [M04 workflow receipt](m04-results.md) maps the local scheduler checks and the three Ship 5 cases. Use the [workflow guide](m04-walkthrough.md) to test a paused version before activation. M06 connects a saved ContextQA replay to the research brief.

## Resume from the implemented application

Start with the [17-module acceptance ledger](platform-acceptance.md) and the individual ticket rows in BACKLOG.csv. For a feature affecting an existing guide, keep the imported baseline, exercise the user journey in Ship 5, review its run/step evidence, and compare the proposed update with that baseline. The [operator guide](platform-operations.md) lists worker bindings, deployer and publication receipts and recovery commands. The [library walkthrough](guide-library-walkthrough.md) illustrates a completed training export and the OpenAPI proposal flow.

## Phase 10 — External integrations

For each affected integration, identify the provider action, the intended consumer outcome, the scoped environment, and the revision or event that joins them. Exercise access denial and a provider failure locally before delivery. On staging, collect the provider receipt and use ContextQA to verify the consumer journey, a dependent resource and an expected failure. Record case, result, revision and documentation disposition. A pending or failed required assertion holds promotion. [GitHub Pages worked example](pages-acceptance.md)

Workspace administrators can set defaults for new briefs using the [writing profile guide and captured form](writing-profile.md).

Before release, record a control and evidence disposition for each applicable OWASP risk. [Phase 11 application security](application-security.md)
