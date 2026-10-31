# EkLine — optional documentation handoff example

**Status: proposed, not executed.** No native session, draft, sandbox connection or
EkLine-created PR is claimed. Historical sign-in readiness does not establish current
Docs Agent access or integration availability.

## Why this example exists

This was originally a proposed “EkLine documenting EkLine” demonstration: document its
own session/review workflow and revise the resulting sample. It was an optional native
editor experiment, not an implemented connector or requirement for the core product.
The original target remains in execution-status.json as historical context.

The current primary path is **customer application → ContextQA tests and execution →
reviewed evidence → client-guided documentation → scoped refresh after changes**.
The repository's own Markdown/HTML outputs do not require EkLine. See the
[usage guide](../../docs/how-to-use.md) and [trigger design](../../docs/documentation-triggers.md).

## Optional role in the current design

If a client already uses EkLine and its current account supports the needed workflow,
it may consume the approved narrative, assets and change brief. This repository does
not automatically invoke EkLine, upload files, connect repositories or create native
PRs. Confirm current supported interfaces before implementing a destination adapter.

1. Use ContextQA to execute the selected customer workflow and collect its actual
   results/media; bind the target revision and review the evidence.
2. Prepare the outline or affected sections under the owner's versioned client
   instructions. The current instruction template is followed by an operator; an
   automatic skill loader is still proposed.
3. Hand off only approved narrative/assets through a supported destination workflow.
   Record a native session or draft identifier only after it actually exists.
4. Review instructions, screenshots, terminology, accessibility and unchanged sections.
5. On a verified application change, use ContextQA impact/capture evidence to prepare
   the scoped refresh. If a separate editor revision is demonstrated, label it as such.
6. Create a draft documentation change only in the authorized destination and with the
   client's approved repository access. Publishing remains a distinct stage.

EkLine's own sandbox/screenshot-refresh behavior is **not** the capture mechanism for
this ContextQA-only lifecycle. The earlier sandbox-refresh proposal is superseded here.
Do not assume a destination can access local asset paths or private evidence links.
No new installation, schedule, permission expansion or publication follows this plan.

## Acceptance and remaining work

A native draft and reviewed update must exist, with working asset links and traceable
ContextQA evidence. Native PR creation must have its own receipt. Until then this is a
handoff runbook, not a runnable sample. No partner relationship or native integration
is implied by mentioning EkLine.

[Historical vendor reference](https://docs.ekline.io/) — revalidate actual account/API
capabilities before implementation; not checked in this documentation update.
