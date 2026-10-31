# ContextQA documentation proof — verification status

Checked October 30, 2026 (America/Chicago). This is an audit and capture request, not a verified application guide.

## Connection and existing evidence

ContextQA MCP read operations succeed for tenant `contextqa-z5`, workspace `Contextqa Z5 / 1.0` (version 1). This connection lists only that workspace, 32 active cases about the ContextQA portal, and no Kan cases. The default environment targets other applications, not Kan. Onboarding is complete.

The user identified the relevant historical evidence in a different tenant: [ship-5 case 167 / result 300](https://ship-5.contextqa.com/run-result-view?testCaseId=167&runResultId=300&isManualExecution=true). That receipt has not been inspected: reconnect MCP to ship-5 first. IDs must never be looked up in a different tenant and treated as the same run. Kan login details are available in the conversation and must enter only an approved secure ContextQA credential mechanism; they are omitted here.

Previously saved contextqa-z5 receipts contain run 1 SUCCESS/completed, run 3 FAILURE/completed, and runs 2/4 QUEUED/in-progress. These are historical plan-level values, not Kan proof. A current MCP case-result lookup for execution 1 returned zero results. The local adapter validation receipt explicitly records zero hosted runs and simulated transport. Earlier non-ContextQA browser evidence remains excluded.

## Mode and capture

Live contextqa-z5 organization settings report `enableAISmartness=EXPERT`, `captureAllStepScreenshots=false`, and `videoRecording=false`. No settings were changed. Inspected local UI options are EXPERT, FAST and STRICT; no Max option is established. These findings do not establish ship-5 capabilities or any equivalence between Expert and Max. Verify the intended tenant's supported mode and per-case recording configuration after reconnecting.

## PR and deployment evidence

- [Kan PR 15](https://github.com/nigharsh/kan/pull/15) is merged. Head: `de9eb589ade097555b573473f9c833192d9af5a2`; merge: `448514ba6f41a8789e4c2307294dc79bdedd6528`. Its historic receipt does not prove current deployment state.
- [Kan PR 18](https://github.com/nigharsh/kan/pull/18) is open at `a0d0587a5f1fe13c0c132e235c6c7148825c2fe5`. Its Vercel status is successful and points to deployment `4kFZTLS3aeK7KqqkfN29Xr5j9THx`. The Vercel preview-comment check refers to a branch preview hostname. Neither proves the requested shared URL `https://kan-qa.vercel.app/` serves that SHA.
- GitHub deployments filtered to PR 18's exact SHA returned an empty list. Listed older deployments refer to Railway. Current shared-target revision remains unverified.
- PR 18's ContextQA impact check reports 32 affected cases and suggestions for review. This is impact analysis, not a workflow execution receipt.

## Trigger review and corrections

Local branch `codex/documentation-refresh-trigger` started at `a30e315`. Remote branch lookup returned 404, no matching PR exists, and the registered GitHub workflows do not include the documentation request workflow.

The request-only integration never starts ContextQA or publishes documentation. Corrections add list creation path mapping, reject duplicate changed-file records that could conceal missing paths, validate rename metadata, and reject a supplied expected head that differs from the PR. The workflow rereads the PR after fetching files and rejects head/base drift. A matching operator-supplied SHA is explicitly labeled as unverified deployment evidence.

The updated request for PR 18 maps checklist, card and list guides. `execution_started=false`, `documentation_published=false`, and `deployment_verified=false` remain explicit.

## Validation and remaining work

80 evidence-package Python tests, 10 mocked AI transport tests, and 12 trigger regression tests pass locally. Diff whitespace checks pass. Kan lint/typecheck were attempted but blocked by pnpm 11.25.0 versus required ^9.14.2. These checks do not execute a browser or establish hosted acceptance.

After reconnecting ship-5: inspect case 167/result 300 and its actual steps/media; resolve Max; bind secure credentials; create an isolated uniquely named board, list and card using only ContextQA; retain run IDs and terminal/per-step outcomes; verify the exact target commit before a PR-specific rerun; collect and review real screenshots/video; export annotated guides and compare the two verified captures. Missing evidence stays missing. No merge or deployment is authorized or performed.
