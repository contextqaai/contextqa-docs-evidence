# Connector capability plan

Reference facts below come from the linked pages in [feature-inventory.md](feature-inventory.md). These are planning inputs, not verified APIs of the providers. Each provider needs a current official API contract, test account and acceptance receipt before shipping. Credentials are secret references, not workspace JSON fields.

| Provider | Reference connection/scope | Role | Build sequence / essential variation |
|---|---|---|---|
| GitHub | App installation; docs repo and product repos | Product source and docs repository | Pilot. Product repo read-only; docs PR writes explicit. |
| ContextQA | Existing scoped adapter/MCP; saved environment/cases/plans | Journey execution and evidence | Pilot. Bootstrap/replay separate; journal non-idempotent starts. |
| GitLab | Token and instance; selected projects/webhooks | Source and docs repository | Later. Validate self-managed support by capability, not connection success. |
| Linear | OAuth; team/projects | Issue source | Later. Separate monitored scope from authorization; backend enforce ours. |
| Jira | Cloud OAuth; selected projects; separate mention app | Issue source | Later. Do not claim Server/Data Center support. |
| Slack | OAuth; selected channels, notifications and users | Research and collaboration | Later. Link Slack users to explicit permissions; no blanket writeback or external messages. |
| Intercom | OAuth; region and workspace | Docs destination and optional ticket source | First candidate external provider; detect provider drafts and per-operation conflicts. |
| Freshdesk | Agent key/subdomain | Docs destination and optional ticket source | Check live-publish entitlement and existing drafts. |
| Help Scout | Docs key and selected site | Docs only | Draft mode may expose metadata immediately; show impact before delivery. |
| Document360 | API token, help URL and project version | Docs only | Require configured version and selected destination; exclude unsupported API-doc versions. |
| Pylon | Admin token and selected KB | Docs only | Token-owner authorship; durable article/container mapping. |
| Zendesk | OAuth/subdomain | Docs and optional ticket source | New articles are drafts; updating content does not itself change publish state. |
| Helpjuice | API key/help URL | Docs | Scope/behavior beyond public overview must be researched. |
| DevRev | PAT/subdomain | Docs and optional ticket source | Scope/behavior beyond public overview must be researched. |
| Salesforce | External client auth; Knowledge field mapping | Docs and optional ticket source | Dedicated project, record types and body/title/path mapping; not a generic article adapter. |
| Mintlify | New path is GitHub docs repo | Repository-backed destination | No new legacy connector. Preserve config/MDX compatibility. |

Common adapter contract: discover capabilities → connect → configure resource scope → assign role → validate/read → sync with cursor → produce proposal → preflight reviewed write → deliver → reconcile receipt → disconnect. A provider may omit operations; the UI hides unsupported actions. A failed enumeration never implies deletion of missing remote content. Each write receives a per-operation outcome so partial success remains recoverable.
