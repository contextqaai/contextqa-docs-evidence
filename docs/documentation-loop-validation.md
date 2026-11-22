# Validation receipt — 2026-11-19

## Implemented application

- Full Python suite: **124 tests passed**, including source normalization, role/assignment boundaries, stale versions, concurrent duplicate intake, baseline drift, exact approval binding, evidence integrity/failure/simulation policies, loopback authentication/origin restrictions and draft-delivery reconciliation.
- Existing optional AI adapter suite: **10 tests passed**, using mocked providers; no paid model request.
- UI helper suite: **4 tests passed**, covering untrusted Markdown, unsafe links, evidence/decision gates and combined inbox filters.
- JavaScript syntax check and Git whitespace check passed.
- Wheel built; package contains all four UI assets and the `cqa-docs-loop` entry point.
- Synthetic account-free workflow: ingestion → individual review → explicit approval → ZIP → local baseline update → duplicate delivery detection passed. This is a software check, not live ContextQA execution.
- Real Kan historical workspace initializer passed independently; no preexisting articles or test passes were fabricated.
- Browser checks at desktop and 390-pixel mobile width: real Kan inbox, three article proposals, article editor/save, unsaved-change cancellation, evidence table, disabled finish-review gate, conditional new-request form. No page-level horizontal overflow at 390 pixels. Fixed a hidden-field CSS regression discovered in that check.
- Configured CI now includes the UI checks and both workspace initializers. No remote CI run receipt is claimed.

## Kan PR #15

Source: https://github.com/nigharsh/kan/pull/15

- PR head: `de9eb589ade097555b573473f9c833192d9af5a2`.
- Recorded merge revision checked out locally: `448514ba6f41a8789e4c2307294dc79bdedd6528`.
- The two focused API test files ran with the installed Vitest binary: **6 passed** (four title-validation parameter cases, two description/optional-title cases).
- Default API TypeScript check **failed** with five TS6142 diagnostics: imports resolve to `@kan/email`'s `.tsx` entry, while JSX is not enabled in the checked configuration. The implementation does not claim an all-green Kan build and does not alter Kan's configuration to hide the error.
- Dependency installation used pinned pnpm 9.14.2 and ignored lifecycle scripts. It reported a missing generated `kan-mcp` executable. Focused tests still ran. This is not a complete production build of Kan.

## Live ContextQA reads

Workspace: Ship 5 / 1.0, workspace version **1**.

- PR impact analysis **19** and historical run **18** were read through ContextQA MCP.
- Run lifecycle: completed. Verdict: **FAILURE**. Counts: **0 passed, 15 failed**.
- Case 143/result 320 and case 137/result 329 depend on `PRE_Login` case 126. Their step-list endpoints returned no workflow steps.
- Failure investigation identified prerequisite step **207**, `verifyCurrentURL`: expected `/boards`, actual `https://kan-qa.vercel.app/boards`. The mismatch occurs before the selected card validation workflow. It must be investigated/corrected before attributing these failures to the PR itself.
- Analysis identified additional coverage needs: blank rename recovery, duplicate-title validation and whitespace trimming.
- Historical documentation result 372 was successful, but is **not** evidence of PR #15 at its expected deployed revision.
- No fresh billed execution, external PR comment, prerequisite mutation, GitHub push, external publication or secret extraction was performed.

Analysis: https://ship-5.contextqa.com/td/1/uploaded-files/pr-impact/19

Run: https://ship-5.contextqa.com/td/runs/18

## Next live acceptance gate

1. Verify the QA deployment's actual commit against the intended revision.
2. Review the full login prerequisite and its current environment variables. Replace the incorrect relative/full URL assertion using a current supported typed action or the resolved full expected URL. Do not simply mark the assertion optional.
3. Preflight the chosen cases/plan, including test-data prerequisites and cleanup behavior. Confirm the execution meter and a bounded run scope before starting the non-idempotent billed trigger.
4. Run the focused create-title checks and the missing rename/trim/duplicate coverage. Preserve actual run IDs and terminal verdicts. A partial or empty result is inconclusive.
5. Capture/review screenshots, export through Docs Evidence, attach to the matching review request, then perform article/editor approval. Until then, the real Kan request remains blocked.

## Release scope

The UI and local review workflow are implemented and checked. Hosted organization authentication, production workers/storage, continuous connectors, independent deployment attestation, live post-fix browser acceptance and media-aware external publication are not complete. The public deployment target and existing ContextQA application repository are still needed to integrate this work into the production product.
