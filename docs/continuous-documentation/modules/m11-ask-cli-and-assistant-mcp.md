# M11 — Ask, CLI and assistant MCP

Status: planned; phase: Parity. Dependencies: M07,M09.

## User outcome

A coding assistant or writer can research and propose docs using the same access rules and durable objects as the app.

## Existing foundation

`agent CLI; no own hosted MCP server inspected`

## Scope and workflow

Contextual chat/history, cited answers, draft requests, status/questions and reusable prompts; remote MCP with consent, selected sites, scopes and revocation. CLI remains available before MCP. Start read/propose-only.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Conversation, AssistantConnection, ScopeGrant; proposed MCP tools: server_info/list_sites/search/get_page/list_inbox/get_run/create_proposal/submit_for_review. Names are design choices, not existing APIs.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M11-T01:** Unify CLI/UI service calls and request IDs.
- **M11-T02:** Implement retrieval with tenant/assignment filters and citations.
- **M11-T03:** Add contextual chat and explicit run proposal.
- **M11-T04:** Expose scoped MCP capabilities and connection/revocation UI with contract tests.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Search cannot expose other tenants, unauthorized drafts or contributor-unassigned proposals.
- AC-2: Repeated client request returns the same run, not a duplicate.
- AC-3: Read-only grant cannot mutate even if a tool name is guessed.
- AC-4: Role reduction/revocation takes effect on the next call.
- AC-5: Draft/submit/merge permissions remain distinct; pilot grants no live-publish capability.

## ContextQA journey and reader guide

**Find an approved answer with a scoped assistant.** As an authorized reader, ask a question, follow its citation to an approved guide and verify its version in the reader. Capture the query and cited answer using test content.

**Negative and recovery coverage.** Revoke or narrow the client grant and repeat the request. Verify denied or filtered content on the next call. Pair the browser evidence with a direct client receipt for the affected CLI or MCP command.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Reference MCP supports selected hosted docs sites, not external help centers. Full-access reference can delegate live publication; our pilot deliberately does not.
