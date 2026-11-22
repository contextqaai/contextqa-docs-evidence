# ContextQA documentation loop

This adds a durable review application to Docs Evidence. It connects product changes to proposed articles, evidence review, editor approval and draft delivery. The included Kan workspace uses real PR #15 and an explicitly historical ContextQA result snapshot. It contains no fabricated passing execution or live-sync status.

## Start the Kan workspace

From the repository root, with Python 3.10+:

```sh
python3 -m pip install --no-deps .
python3 examples/kan-pr15/prepare.py --db private/kan-review.db
cqa-docs-loop --db private/kan-review.db --project kan serve
```

Open the secure localhost link printed by the server. The random session token is stored in the tab's session storage and removed from the address bar. Keep the database private. Restarting the server creates a new session token. Reopen that new link after a restart. The example initializer requires a new database/project; it does not overwrite an existing review.

Use the review inbox to inspect the source, compare or edit each article, assign a reviewer, accept/dismiss/undo individual changes and discuss the request. The Knowledge base contains approved local baselines; pending proposals remain in the inbox. Sources identifies snapshot imports honestly. Content health checks age, missing mapped coverage and relative Markdown links. It does not perform semantic drift detection or crawl external URLs.

The product UI provides responsive navigation, searchable/filterable requests, persistent Markdown editing, preview, evidence details, activity, explicit review handoffs, custom dialogs, focus styles, loading/error/empty states and protection against accidental unsaved navigation. Failed or missing evidence keeps delivery unavailable. Accepting one article is not approval to publish.

## Developer workflow

1. **Bind the product.** Put repository, deployment URL, expected revision, writing instructions, owners and code-to-document mappings in the manifest. The product under test here is Kan at `kan-qa.vercel.app`; `ship-5.contextqa.com` is the testing workspace. They serve different purposes.
2. **Read the PR.** Retrieve the exact diff and head/base/merge identities. GitHub merged-PR webhook normalization verifies HMAC, repository and merge state. GitHub's webhook payload does not contain the file diff: retrieve that separately with least-privilege credentials before adding changed paths or replacement text. Duplicate event IDs are idempotent only when their content is unchanged.
3. **Map documentation impact.** Code paths, module IDs and explicit article selection identify likely sections. Keyword matches are labeled as requiring relevance review. An unmatched event becomes a question, not an invented article. Import complete replacements against exact existing Markdown, or `before: ""` for new articles.
4. **Use ContextQA MCP interactively.** Verify the active workspace, inspect PR impact, saved test cases and prerequisites, diagnose results, and use current action catalogs for any authoring. Here workspace version 1, PR impact 19, and run 18 were inspected. MCP session access does not provide a reusable API token for CI.
5. **Use ContextQA APIs in CI.** Use the repository's existing contract-derived adapters and a scoped secret-manager token. Preflight the saved plan/profile, trigger once only after bounded execution authorization, journal the returned run ID, poll to a terminal state, and collect selected result hierarchy. Never retry an ambiguous execution trigger. See [API contract](contextqa-api.md) and [platform workflow](contextqa-platform.md) for the supported routes and commands; do not infer routes from browser URLs.
6. **Review execution and media.** Completed is not synonymous with passed. A failed prerequisite, absent steps, zero executed cases or missing media cannot satisfy the capture requirement. Collect only selected results; fetch approved media explicitly without forwarding the API token to artifact hosts. Keep raw results/signed links private. Human-review the export through the existing Docs Evidence approval/export flow.
7. **Attach reviewed evidence.** Use the command below against the current review version. Export integrity, execution verdict, simulation policy, required screenshots and expected commit metadata are checked. A capture's commit metadata is not independent deployment attestation: verify that the deployed application really served that revision before approving the article.
8. **Review and deliver.** Resolve questions, decide every article, finish review, then approve the exact content/evidence digest. Download the draft ZIP or explicitly create a text-only draft PR. Apply locally only after reviewing the downloaded result. No automatic merge or website publication occurs.

```sh
cqa-docs-loop --db private/kan-review.db --project kan state
cqa-docs-loop --db private/kan-review.db --project kan evidence ITEM_ID private/reviewed-export --version CURRENT_VERSION
```

The evidence command takes an existing reviewed export directory, never a remote URL. A contributor can review assigned items but cannot approve/deliver them. These are local workflow roles, not organization SSO identities.

## Draft GitHub delivery

The bundle contains `delivery.json`, exact Markdown replacements under `docs/`, `changes.patch`, and reviewed evidence files when present. Paths in the manifest are relative to the target documentation repository; place the right prefix in the manifest before proposing a change.

The optional `draft-pr` command reads a local checkout, checks its GitHub origin and exact base SHA, verifies the remote base branch and article baselines, builds in a separate temporary clone, commits, pushes a unique branch and creates a draft PR through authenticated `gh`. It never merges. A durable intent journal prevents automatic replay after uncertain push/PR responses.

```sh
cqa-docs-loop --db private/kan-review.db --project kan draft-pr ITEM_ID \
  --checkout /absolute/path/to/docs-checkout \
  --base-sha FULL_REVIEWED_40_CHARACTER_SHA --base-ref main \
  --branch contextqa-docs/unique-review-id --journal private/delivery-intent.jsonl \
  --confirm-create-draft-pr
```

This is an explicitly invoked remote write. Inspect the local bundle before invoking it. No remote delivery was executed during this implementation. The adapter currently accepts **text-only** bundles; evidence-bearing bundles must be delivered using the ZIP after choosing media deployment paths. If a delivery fails, reconcile the branch/PR recorded in the journal; do not delete the journal and blindly repeat. Bundle creation is recorded as a local delivery even if subsequent remote delivery fails.

## Intake and automation boundaries

`ingest` accepts normalized manual/GitHub/Linear/Jira/Slack/video/audit events. Only GitHub has signature-aware normalization here; the presence of the other names does not imply installed OAuth integrations. `video` accepts an existing transcript with explicit, source-matching segments and timestamp bounds. It does not transcribe video, select frames or record a browser session. Optional BYOK drafting in the existing repository is separate and requires its explicit data-sharing flag.

SQLite transactions serialize mutations. Expected review versions and article digests reject stale writes. Editing, commenting, assignment or evidence changes invalidate an approval. Delivery revalidates evidence and baseline hashes. Bundles are bounded to 16 MiB of reviewed evidence. The GitHub adapter and test execution adapters use explicit intent records for non-idempotent writes.

## Production deployment boundary

The redesigned UI is implemented and browser-checked, but this repository is **not yet a production SaaS deployment**. The included server deliberately binds only to loopback and authenticates one operator. Do not put it behind a public tunnel and call it production.

Before serving multiple organizations, implement organization authentication and session lifecycle, tenant isolation tied to authenticated identities, durable worker scheduling and webhook receipt storage, managed database migrations/backups, private object storage and retention, connector token management, audit retention, observability, rate limits and operational recovery. Validate concurrent workers, permission boundaries, failure recovery, browser coverage and accessibility with the deployment's actual identity provider and infrastructure. Native publishing integrations, unattended recapture and automatic deployment-revision attestation remain outstanding.

The current implementation is usable for an operator-led developer review workflow. Its production interface does not conceal those runtime and integration limits.
