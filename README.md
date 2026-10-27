# ContextQA documentation evidence

ContextQA Docs Evidence helps solutions engineers and technical writers turn reviewed workflow evidence into documentation they can refresh when the app changes. Run this experimental local wrapper to review and export a guide; browser capture comes from a separate producer.

**Workflow:** capture a known task → select screenshots → attach to instructions → review → export a guide → repeat after a release → supply change context → compare explicitly matched steps → review the documentation update.

Built around [ContextQA](https://contextqa.com/?utm_source=github&utm_medium=developer_referral&utm_campaign=contextqa_docs_evidence&utm_content=readme_overview) workflow evidence. Start with the [recorder guide](https://contextqa.com/tutorials/no-code-test-automation-recorder/?utm_source=github&utm_medium=developer_referral&utm_campaign=contextqa_docs_evidence&utm_content=readme_capture_guide) or read about [visual baselines and change review](https://contextqa.com/blog/visual-regression-testing-ui-stability/?utm_source=github&utm_medium=developer_referral&utm_campaign=contextqa_docs_evidence&utm_content=readme_visual_regression_blog).

**Release status:** private candidate; an open-source license and public release are pending owner approval. Core local samples make no model or ContextQA SaaS calls. Optional AI and hosted execution use separate credentials and may incur provider charges.

## What works now

- Import candidate actions and screenshot frames from bounded Playwright trace ZIPs. Raw trace, DOM and network details stay private.
- Attach local PNG/JPEG/WebP screenshots and independently recorded MP4/WebM videos to steps.
- Read explicitly selected ContextQA result records using an environment token, without executing paid runs or downloading remote media.
- Require content/media review, bound to hashes, before exporting Markdown with attached images, a static HTML walkthrough, JSON, an iframe snippet and partner handoff instructions.
- Compare reviewed before/after exports with release context and explicit step matching. Produce a documentation refresh draft and machine-readable changes.

The wrapper does not capture browsers itself, infer which screenshot belongs to which step, perform pixel/semantic regression analysis, update external documentation automatically, create a live application clone, or call undocumented partner APIs. Comparison reports changed text or media hashes; animation, timestamps or encoding can change hashes without meaningful UI changes.

## Quick start (Python 3.10+; no runtime dependencies)

Run from this directory, or install with `python3 -m pip install .` and use `cqa-artifacts`.

```sh
python3 -m cqa_artifacts init workspaces/release-a --title 'Create a project — release A'
python3 -m cqa_artifacts add-step workspaces/release-a --title 'Open Projects' --instruction 'Select Projects in the left navigation.'
python3 -m cqa_artifacts add-media workspaces/release-a --kind screenshot --file /absolute/path/reviewed-screenshot.png
# Use the returned media_id:
python3 -m cqa_artifacts attach workspaces/release-a --step 1 --media-id MEDIA_ID
python3 -m cqa_artifacts approve workspaces/release-a --reviewer 'Documentation owner' --confirm-rights-and-reviewed-content
python3 -m cqa_artifacts export workspaces/release-a --out exports/release-a --base-url https://docs.example.com/walkthroughs/release-a
```

The base URL generates an embed snippet; nothing is hosted or uploaded. `guide.md` uses relative image attachments. When moving a guide into a docs system, upload its assets and rewrite relative links for that system. Keep video attachments separate if the destination cannot embed them.

Only confirm review after inspecting every selected frame/video for personal data, credentials, proprietary content and metadata, and verifying permission to share it. Text filtering is incomplete and never sanitizes pixels or video audio. The CLI is a trusted single-user local prototype, not a multi-tenant security boundary.

## After the app changes

Capture the same task under the same role, locale, viewport and seeded data on the new version. Create and review a separate workspace/export; preserve the baseline. Copy `examples/change-context.json`, then edit the version labels, actual change explanation, affected documents and step mapping.

```sh
python3 -m cqa_artifacts compare exports/release-a --after exports/release-b --context examples/change-context.json --out exports/change-review
```

Every old and new step must be mapped exactly once. `null` marks an added or removed step; reordered steps can be paired explicitly. Both exports need unchanged review receipts. Read `refresh-draft.md` alongside both exports; `changes.json` identifies their step numbers and attached media IDs. The comparison HTML includes only media from the two reviewed exports, labeled Before and After. Approval does not establish that product behavior is correct or that a claimed change actually happened.

## Existing evidence sources

```sh
python3 -m cqa_artifacts import-trace workspaces/release-a --file /absolute/path/trace.zip
python3 -m cqa_artifacts edit-step workspaces/release-a --step 1 --title 'Open Projects' --instruction 'Select Projects in the left navigation.'
python3 -m cqa_artifacts inspect workspaces/release-a
```

A trace is not a complete video. Record video separately if required. Imported action parameters, selectors, filled values, network responses and DOM snapshots are not copied into public output. Trace frame extraction is a bounded, best-effort parser for the observed NDJSON event shape; Playwright's internal archive format can change.

For read-only ContextQA collection, inject `CONTEXTQA_API_TOKEN` with your existing secret manager or local environment. Never put it in a command argument, source file, issue or PR.

```sh
python3 -m cqa_artifacts collect workspaces/release-a --run-id RUN_ID
```

Optional `--case-result-id ID` and `--step-result-id ID` require appropriate scopes and verifiable parent-run relationships. Missing parent fields fail closed. Signed media references remain under `private/`; fetch/review media separately using an authorized first-party download flow. No remote asset fetch, arbitrary URL, browser execution or paid-run endpoint is implemented.

## Documentation

- [Use cases and partner workflows](docs/use-cases.md)
- [Capture and refresh playbook](docs/capture-and-refresh.md)
- [Growth experiment](docs/growth-experiment.md)
- [Security and publication boundaries](docs/security.md)
- [Sources and capability limits](docs/sources.md)
- [Browser automation product scope](docs/product-scope.md)
- [ContextQA resources and attribution](docs/contextqa-resources.md)

## Native platform lifecycle examples

The examples use **Layerpath itself** and **EkLine itself** as their documentation targets:

- [Layerpath authoring lifecycle](examples/layerpath-lifecycle/README.md): real creation/editor workflow, private tour, controlled revision and evidence refresh.
- [EkLine documentation lifecycle](examples/ekline-lifecycle/README.md): real Docs Agent session, reviewed draft, controlled revision and scoped PR/screenshot refresh.
- [What remains to finish automation](docs/completion-requirements.md): required access, implementation and acceptance evidence for each missing capability.

**Status:** the user reported sign-in complete for both platforms; feature access and native lifecycle execution remain unverified. These are executable runbooks, not receipts claiming completed native projects. The text-only synthetic demo below is a separate wrapper check.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 examples/demo.py /tmp/cqa-docs-evidence-demo
```

The demo uses synthetic instructions only; it does not claim to record a real app or create video. Source code and documentation may be shared separately from customer evidence. No open-source license has been granted in this private prototype.

## Optional AI with your own key

Use OpenAI, Claude/Anthropic or an OpenAI-compatible provider from your own local process. [Provider configuration, consent, usage metrics and privacy](docs/ai.md). AI drafts require explicit sharing approval and never execute browser actions, approve evidence or publish content. Keys stay in environment variables or your secret manager.

## Product strategy and release plan

[Growth strategy and two-recipe specification](docs/GTM.md) · [Capability evidence](docs/capability-register.md) · [Prioritized implementation backlog](docs/backlog.md) · [Audience and fair comparisons](docs/comparisons.md). These are local release drafts; proposed API flows, commands and commercial claims are explicitly gated. No public open-source release or hosted service is implied.
