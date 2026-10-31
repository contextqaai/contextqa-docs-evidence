# Documentation triggers and GitHub Actions

Use two stages: **change detected → refresh requested**, then **deployment verified →
ContextQA capture eligible**. A PR does not itself prove that a new UI is deployed.
This repository currently implements the Kan request mapper, not the complete event
receiver, execution queue, selective generator or documentation publisher.

## Which trigger does what?

| Event | Intended action | Current implementation |
| --- | --- | --- |
| ContextQA onboarding/crawl/test generation completes | Propose outline; map workflows/tests/modules; queue first reviewed baseline | Proposed consumer; generated cases are not verified docs |
| PR opened, updated, reopened, ready for review | Determine affected tests/modules and documentation sections; prepare request | Kan path mapper + request-only Actions example |
| Deployment succeeds | Verify target URL/environment/full SHA; unblock the matching request | Proposed deployment verifier/orchestrator |
| ContextQA execution completes | Retrieve durable verdict/selected media; draft verified sections or record blockers | Operator collection supported; automatic receiver not implemented |
| Client instruction file changes | Redraft affected presentation/text under approved instructions | Manual today; no automatic skill loader |
| Manual operator request | Select PR/revision/workflow to inspect or refresh | Kan request workflow supports manual PR input; live run is separate |
| Scheduled drift check | Compare current evidence periodically where no code event is available | Proposed; needs explicit schedule and execution policy |
| External CI/release webhook | Send authenticated event to the same queue or GitHub repository_dispatch | Proposed integration; no webhook URL supplied by this repo |

Repository connection is optional. Without it, use workflow identity and approved
release/manual triggers; do not claim automatic code-impact mapping. A change in
configuration or feature flags may also require recapture without a code diff.

## Working example: Kan PR capture requests

The complete [request workflow](../examples/documentation-lifecycle/kan-request.workflow.yml)
is a copy of the reviewed Kan workflow at commit
`14a0a441a30a1e95bab4009d079183c0f8062dfc`. It is stored under examples, not installed
as an active workflow in this repository. It uses:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  workflow_dispatch:
    inputs:
      pull_request:
        description: Pull request number to inspect
        required: true
        type: string
permissions:
  contents: read
  pull-requests: read
```

Its job reads the PR and complete changed-file list, rejects head/base drift, runs
mapper regression checks, prepares `docs-refresh-request.json`, and uploads it as an
artifact. It carries no ContextQA token and cannot execute a test or publish docs.
Cancelling an outdated request-generation job is safe because this stage starts no
remote execution.

For **nigharsh/kan only**, install the following reviewed files in the application
repository on a review branch:

- Copy the example YAML to `.github/workflows/docs-evidence.yml`.
- Copy this repository's `integrations/kan/docs_request.py` to
  `.github/contextqa_docs_request.py`.
- Retain the matching `.github/test_contextqa_docs_request.py` from
  [Kan PR 19](https://github.com/nigharsh/kan/pull/19), which contains the three-file
  integration and its documentation. Use the exact reviewed commit above.
- Review the workflow installation and open a PR. Do not add live secrets for this stage.

The mapper is intentionally scoped to `nigharsh/kan` and hardcodes Kan path rules and
target URL. **Do not copy it to an arbitrary client repo and assume it becomes generic.**
General clients need a configurable, validated mapper/manifest and repository identity
checks first. Upstream ContextQA module/test impact should eventually feed that mapping;
the current path mapper is not a semantic module-impact implementation.

[Run 41170081040](https://github.com/nigharsh/kan/actions/runs/41170081040) verified the
PR-open request path and uploaded artifact on PR 19. Its CI-only changes mapped to zero
application workflows; this is not proof of a nonempty hosted capture. PR 18's nonempty
card/list/checklist mapping was separately checked locally. `execution_started=false`,
`deployment_verified=false` and `documentation_published=false` remain explicit.

## Deployment-ready trigger shape (proposed)

The following is an **illustrative event/job fragment**, not a runnable capture
workflow. The referenced adapter scripts must be implemented and reviewed first.
Do not paste it into production and replace missing commands with success messages.

```yaml
on:
  deployment_status:
  repository_dispatch:
    types: [contextqa-docs-deployment-ready]
  workflow_dispatch:
    inputs:
      request_id:
        required: true
        type: string
permissions:
  contents: read
jobs:
  verify-and-enqueue:
    if: >-
      github.event_name != 'deployment_status' ||
      github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    # Proposed adapter, intentionally not an executable command:
    # 1. Read the event JSON as data, never interpolate it into shell code.
    # 2. Authenticate/reconcile the delivery and load the stored request.
    # 3. Query the trusted deployment provider; verify URL, env and SHA.
    # 4. Bind the PR head or merge/squash commit relationship explicitly.
    # 5. Enqueue one deduplicated capture under the approved execution policy.
    # Required checkout and adapter steps are intentionally omitted.
```

A deployment event is a candidate, not attestation by itself. Allowlist environment,
repository and application origins. Resolve branch-preview aliases to the actual
revision, or require a trusted deployment-provider receipt. Reject mismatches. For
post-merge builds, the expected deployment commit may differ from the PR head.
Do not set the expected revision from the workflow's default `GITHUB_SHA` for every
event; inspect the documented event-specific fields and verify against the provider.

Use a trusted default-branch control-plane implementation for privileged execution;
never run PR-supplied scripts with ContextQA or publication credentials. A deployment
URL is untrusted input until validated. Keep secrets in ContextQA/secret storage and
out of event payloads. Do not use `pull_request_target` to execute untrusted PR code.

## The proposed capture worker

The worker can live in ContextQA's backend or a separate controlled job. It should:

1. Load the project, tenant/workspace, approved instruction version, impacted sections
   and verified deployment receipt from durable storage.
2. Verify the plan/cases/environment and authorized isolated dataset. Upstream impact
   analysis may mark cases UPDATE/RERUN/ADD; finish necessary test edits before capture.
3. Persist an execution intent before a single ContextQA start, then persist the
   accepted run ID. Poll that ID within bounds. Resume reads after a timeout.
4. Collect terminal result/step hierarchy and actual media. If the run fails or evidence
   is incomplete, leave the prior published guide intact and produce a blocker report.
5. Generate only affected sections, preserving stable IDs and manual edits. Attach
   revision, instructions hash, test/run IDs and media digests.
6. Review privacy, brand instructions and before/after differences, then create a draft
   documentation PR. A separate approval/publishing stage controls publication.

Suggested deduplication identity: project + tenant/workspace + workflow + deployed SHA
+ instructions hash + capture configuration + refresh purpose. A deliberate new
recapture gets a new attempt identity; duplicate event deliveries do not. Keep a durable
ledger beyond GitHub artifact retention. Concurrency groups alone are not exactly-once
execution. Cancelling a GitHub job does not cancel a ContextQA run. Never automatically
retry a potentially accepted non-idempotent start.

Suggested states:

```text
requested → awaiting_deployment → ready_for_capture → execution_started
          → evidence_collected → review_required → approved → published
```

Also preserve `blocked`, `failed`, `superseded`, `no_documentation_change`, and
`execution_outcome_unknown`. These are proposed controller states, not current API enums.
A code-only refactor can yield reviewed `no_documentation_change`; changed bytes alone
must not force a rewritten page. A new feature with no test mapping needs coverage work.

## Run-completed events and non-GitHub triggers

Use a supported ContextQA completion event/webhook when the tenant exposes one; verify
its signature, tenant and event identity, then reread the durable result through the
supported API. Do not invent a webhook contract. If no such integration is available,
a worker can poll the known accepted run ID. Never interpret delivery as test success.

An external CI system can call a future authenticated receiver or dispatch a GitHub
`repository_dispatch` event. For example, a **proposed payload contract** might be:

```json
{
  "event_type": "contextqa-docs-deployment-ready",
  "client_payload": {
    "request_id": "example-request-123",
    "project_id": "example-project",
    "deployment_receipt_id": "example-deployment-456"
  }
}
```

IDs are references, not credentials or proof. The receiver must resolve trusted records
and enforce scope. Use a server credential with the narrow required repository access;
never put application login data, API tokens or arbitrary shell commands in the payload.
No request is sent by this example.

For brand changes, watch the controlled documentation-instructions paths and record a
new approved version. For scheduled checks, make the desired scope/frequency explicit;
start with draft-only output, prevent overlapping work and report meaningful failures.
For releases, wait for deployment confirmation instead of assuming a published release
is live. Avoid event loops: documentation-only PRs should not retrigger application
recapture; baseline and policy changes should have their own event classification.

## GitHub platform details and sources

GitHub's documented event rules matter: `repository_dispatch`, scheduled runs and
`workflow_dispatch` require the workflow file on the default branch; scheduled runs use
that branch. Deployment status events with state `inactive` do not trigger workflows.
An Actions run does not guarantee application deployment identity. Sources checked
October 31, 2026:

- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Deployment status events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#deployment_status)
- [Repository dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)

## Acceptance before enabling automation

Prove one real request → exact deployed revision → ContextQA run → reviewed evidence →
draft documentation change. Then exercise duplicate delivery, stale PR head, failed or
empty run, missing media, deployment mismatch, unsupported mode, unapproved instructions
and a style-only change. No case should silently publish an unsupported claim. Until
that lifecycle has receipts, describe the integration as request preparation plus an
operator workflow, not automatic documentation maintenance.
