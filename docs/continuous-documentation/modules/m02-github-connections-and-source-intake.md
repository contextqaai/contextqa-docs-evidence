# M02 — GitHub connections and source intake

Status: implemented locally, in acceptance review. See the [M01/M02 results](../m01-m02-results.md) and [operator workflow](../m01-m02-operations.md). Pilot phase. Dependencies: M01.

## User outcome

An admin selects exactly which product code to read and which docs repository to update.

## Existing foundation

`loop_sources.py; agent.py; .github/actions/docs-agent`

## Scope and workflow

GitHub connection/installation health, separate product/docs selections, branch/root, webhook endpoint, source-event ledger, reconnect/disconnect and manual/CLI intake. Connection success, completed configuration and active workflow are distinct.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Connection, ResourceScope, SourceEvent; unique organization/provider/delivery key; proposed connections APIs and signed webhook endpoint.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M02-T01:** Implement credential-reference and authorized repository discovery/configuration.
- **M02-T02:** Persist signed webhook events before acknowledging; normalize through loop_sources.
- **M02-T03:** Connect CLI/CI submissions to the same event identity and hosted run.
- **M02-T04:** Expose source health and reconnect; pause reads/writes when disconnected.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Replayed delivery produces one logical event and one eligible run.
- AC-2: Invalid signature or unselected repository produces no run.
- AC-3: Code repositories remain read-only; docs delivery uses the explicitly chosen repository.
- AC-4: Default-branch merged event and deployed revision remain separate fields.
- AC-5: Disconnect stops future intake and clearly reports what external app installation remains.

## ContextQA journey and reader guide

**Connect product and documentation repositories.** As an admin, choose separate product and docs scopes for a test installation. Submit a selected branch event and inspect its source revision and intake receipt. Capture the scope summary and the event detail.

**Negative and recovery coverage.** Replay the delivery ID and verify a single logical event and eligible run. Send an event from an unselected test repository and confirm no run is created.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred: GitLab and issue/chat providers to M12. Never import credentials or suspected secret files into writer context.
