# What has been built, and what remains

The current project is a documentation-evidence wrapper. It is not a deployed replacement for hosted browser infrastructure. ContextQA already exposes workflow/test execution and result capabilities, but this repository only reads explicitly selected results and processes local evidence.

| Capability | Current implementation | Additional work for a browser automation product |
| --- | --- | --- |
| Reusable documentation evidence | Reviewed steps/media, Markdown, static HTML, iframe snippet | Stable workflow identity and destination asset adapters |
| Release-aware updates | Explicit version/change context and paired step comparison | Release event ingestion, affected-doc mapping and recapture |
| Browser actions | Existing platform/recorder supplies evidence; wrapper does not drive browsers | Supported action API, session lifecycle and browser runtime |
| Live browser access | Not implemented | Authenticated sessions, CDP/WebSocket or supported action transport, live view and termination |
| Execution reliability | Read-only wrapper avoids paid execution | Idempotency, cancellation, timeouts, durable run state and retry rules |
| Hosted multi-user product | Not implemented | Tenant isolation, scoped credentials, quotas, audit logs and retention |
| Concurrency and scale | Not implemented | Capacity management, queues, browser isolation and load tests |
| Billing | Experiment proposal only | Metering, cost controls, plans, billing and support ownership |
| Partner publishing | Manual reviewed handoff | Verified partner APIs and independently approved publication |

## Next useful product milestone

Validate a **workflow-to-evidence API** using existing ContextQA capabilities: accept an approved task/version, execute within scoped limits, return protected screenshots/video/steps and a reviewed evidence package, then recapture affected tasks after changes. That milestone still requires engineering and live acceptance tests; this repo does not expose a hosted endpoint for it.

A general-purpose browser-session product is a later decision. Do not market this wrapper as a live browser provider or promise arbitrary browser access, automatic documentation synchronization or production service guarantees.
