# Layerpath integration brief

For Vinay and the Layerpath team: use ContextQA as the workflow execution provider,
and this repository as the evidence collection, review and comparison layer beneath
your demo-authoring workflow. This is a starting point for integration, not a
ready-to-use Layerpath backend.

**Status:** the ContextQA client and local evidence tools are implemented; the
Layerpath handoff is proposed and manual. No Layerpath connector or completed native
create/update/publish lifecycle is demonstrated. See the
[execution status](../examples/layerpath-lifecycle/execution-status.json).

## Responsibilities

| Component | Responsibility and boundary |
| --- | --- |
| ContextQA | Execute configured customer workflows and supply results and available media. Saved plans own browser execution, prerequisites and configured environments. Tenant access and capture behavior need validation. |
| This repository | Collect selected results, attach explicitly selected media to steps, require review, export local evidence packages and compare reviewed versions. It does not run a browser itself. |
| Layerpath | Intended destination for authoring and presenting the interactive demo. Supported asset intake, scene editing and update interfaces must be confirmed with the Layerpath team. |
| Integration to build | Map evidence to Layerpath scenes and coordinate supported native updates. Deployment triggers, automatic recapture and publication require additional implementation and acceptance. |

Vinay can reuse the ContextQA execution path instead of building another browser
runner for this workflow. Installing this repository alone does not provision that
service, create runnable tests from an arbitrary URL, or establish API entitlement.

## One baseline-to-refresh walkthrough

### 1. Install and configure the evidence source

From the repository checkout, use Python 3.10+:

```sh
python3 -m pip install .
python3 -m cqa_artifacts contextqa-operations
```

Configure the target application, authentication, isolated test data, capture settings
and a saved plan in ContextQA. Use actual tenant IDs. An authorized superadmin obtains
a scoped token through Settings → API tokens; inject `CONTEXTQA_API_TOKEN` through a
secret manager or private process environment. Python does not automatically load
`.env`. See [API setup and scopes](contextqa-api.md) and
[saved-plan configuration](contextqa-platform.md).

The local client exposes 26 contract-derived JSON authoring/result operations plus a
separate saved-plan trigger. Relevant upstream routes include
`GET /test_plans/{id}/execution`, `GET /test_plan_results/{id}/results`, and selected
case/step result reads. These are ContextQA routes, not Layerpath APIs. The client
uses `https://server.contextqa.com`; its implementation tests use simulated transport
and do not establish live acceptance for every tenant.

For an account-free introduction, run `python3 examples/contextqa_demo.py` with a new
output-directory argument. That example simulates API responses; it does not capture
an app or prove a Layerpath integration.

### 2. Execute once and collect selected evidence

Use an existing authorized result, or follow the
[run-once and bounded-poll procedure](contextqa-api.md#start-once-then-poll-the-accepted-run)
for the approved saved plan. Execution may bill; the trigger is non-idempotent and
the supplied token contract has no cancel endpoint. Reconcile ambiguous starts
instead of retrying them.

Create an empty workspace and substitute verified integer result IDs:

```sh
python3 -m cqa_artifacts init workspaces/release-a --title 'Customer onboarding'
python3 -m cqa_artifacts contextqa-collect workspaces/release-a \
  --run-id PLAN_RUN_ID --case-result-id CASE_RESULT_ID \
  --step-result-id STEP_RESULT_ID --import-steps
```

The plan-run, case-result and step-result IDs must belong to the same selected
hierarchy. Imported steps are candidates, with no automatically attached screenshots.
Inspect and edit instructions against observed behavior. Retrieve selected media
using `fetch-media` only with its reviewed exact storage host, or attach an already
retrieved local file. See [media retrieval](contextqa-api.md#october-30-selected-media-retrieval).

```sh
python3 -m cqa_artifacts add-media workspaces/release-a \
  --kind screenshot --file /absolute/path/to/reviewed-contextqa-frame.png
# Replace MEDIA_ID with the returned ID and choose the matching step explicitly.
python3 -m cqa_artifacts attach workspaces/release-a --step 1 --media-id MEDIA_ID
```

Repeat for the selected workflow. Review screenshot pixels and any recording audio;
text filtering does not sanitize them. Keep raw results, traces and signed URLs private.

### 3. Review, export and hand off to Layerpath

After inspecting the complete selected content and its sharing rights:

```sh
python3 -m cqa_artifacts inspect workspaces/release-a
python3 -m cqa_artifacts approve workspaces/release-a \
  --reviewer 'Documentation owner' --confirm-rights-and-reviewed-content
python3 -m cqa_artifacts export workspaces/release-a --out exports/release-a \
  --base-url https://docs.example.com/walkthroughs/release-a
```

The local export includes `guide.md`, `manifest.json`, selected `assets/`, a static
`index.html`, a review receipt, an iframe snippet and `handoff.json`. Nothing is
uploaded or hosted. The example base URL only supplies the future iframe target;
replace it with your intended hosting URL. The HTML is a static walkthrough, not a
live application clone.

`handoff.json` labels Layerpath's mode `manual_media_import`: use approved images or
video and reviewed steps as the project brief. It is not a vendor import schema and
does not call Layerpath. If the account supports the required intake, create a private
demo through supported Layerpath controls, then check scene order and any supported
hotspots, branches and navigation. Keep the actual project/scene identifiers for
future mapping only after they exist.

### 4. Refresh after an application change

Recapture the same workflow in ContextQA against the intended new application version,
keeping role, locale, viewport and seeded data comparable. Review and export a separate
`release-b`; preserve the baseline. Copy and edit
[change-context.json](../examples/change-context.json) with the actual release context
and explicit old/new step mapping, then run:

```sh
python3 -m cqa_artifacts compare exports/release-a \
  --after exports/release-b --context private/change-context.json \
  --out exports/change-review
```

Every old and new step must be mapped exactly once; use null for additions/removals.
Review `refresh-draft.md`, `changes.json` and the before/after HTML. Comparison detects
text/media identity changes, not semantic UI changes. A changed screenshot hash cannot
validate a hotspot or prove a meaningful product change.

Use the reviewed comparison to replace affected scenes through supported Layerpath
controls, preserving unaffected content. Recheck navigation and obtain the owner's
publication approval. Automatic scene replacement is not implemented.

## Interface decisions to confirm with Vinay

These are proposed requirements for a future adapter, not existing Layerpath fields
or endpoints:

| Decision | Information needed |
| --- | --- |
| Supported intake | Manual upload, supported API or another documented mechanism; accepted image/video formats, limits and account entitlement. |
| Authentication | Supported credentials/scopes and tenant/project access boundaries, if an API exists. No Layerpath credential setup is supplied here. |
| Scene mapping | How a stable workflow/step identity maps to an actual Layerpath project and scene; how additions, deletions and reordering are represented. The current comparison uses explicit step mappings. |
| Update behavior | Whether assets/text can be replaced while retaining hotspots, branches, links and manual edits; conflict and retry behavior. |
| Review and publication | How to create a private draft, review changes, publish an approved version and recover a previous version using supported controls. |
| Provenance | Where to retain source run IDs, reviewed export digests, application revision and destination revision without exposing private source records. |

## Remaining work and acceptance

There is no implemented Layerpath authentication adapter, asset-import API, scene
mapping store, native update/export/publish automation or verified native lifecycle.
Current account feature access also remains unverified. The historical vendor link
in the [Layerpath runbook](../examples/layerpath-lifecycle/README.md) must be revalidated
before implementing an adapter.

For unattended refresh, deployment verification, event handling/deduplication,
execution coordination and selective regeneration still need implementation. The
existing Kan integration prepares capture requests only; see
[documentation triggers](documentation-triggers.md). Client instruction and
section/test/module templates are not automatically loaded by this CLI.

A useful first acceptance exercise is one private customer workflow and one verified
application change: obtain real ContextQA evidence, create a Layerpath demo through
confirmed supported intake, update only affected scenes, verify navigation and retain
reviewed before/after provenance. Record supported and unsupported features explicitly.
Until that succeeds, describe this as an integration starting point with a manual
handoff, not an automatically maintained Layerpath demo.
