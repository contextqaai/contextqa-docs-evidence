# M00 workspace foundation

The default landing page is Overview. An editor can open a request needing evidence, import an article baseline, or create a request. Contributors see their assigned queue. Execution summaries link to the corresponding review and come from imported source records. A request's age, a downloaded bundle, and the presence of an article baseline each have distinct meanings. The overview makes no publication or live-run claim.

## Route audit and implemented behavior

All screens retain the existing query URL format so previously shared review links still open. The workspace key is recorded in the URL on first access. Future setup, workflows, capture management, and publication screens are specified in the [roadmap](roadmap.md).

| Entry | Data and action | Recovery and boundary |
|---|---|---|
| Overview | Scoped state supplies open requests, questions, imported execution summaries, and baseline count. Editors enter the existing intake forms. | Empty states explain how to begin or how assignments arrive. |
| Review inbox | Filter and open requests from the scoped snapshot. | Contributor visibility is enforced by the existing backend. |
| Request detail | Review a change, read supporting evidence, edit Markdown, and approve a revision. | Preserve draft-discard confirmation. Tablet and mobile users can toggle request details. Mobile users can choose an article with a native select. |
| Knowledge base | Inspect baselines and import Markdown. | An editor can import the first article from the empty workspace. |
| Sources and evidence | Inspect recorded GitHub and ContextQA source information. | Managed connections and capture configuration belong to M02 and M06. |
| Content health | Query the scoped audit and open a request or import from a finding. | Existing retry and missing-coverage paths remain available. |
| Activity | Read scoped audit history. | Delivery and publication receipts are specified in M09. |
| Settings | Read workspace configuration and review policy. | Membership and onboarding changes belong to M01. |

The shared sidebar and design tokens live in the web app. The workspace loader clears scoped content on a switch and ignores superseded reads. Failed project discovery and failed snapshot loads can both be retried. Mobile navigation supports Escape and a close button. Existing dialogs return focus to their opener.

## Verification

Based on the local merge of PR #10 at `1d62a9a`. The implementation-pass checks below predate the five Ship 5 acceptance runs. See the current results below.

| Check | Result |
|---|---|
| Python wrapper and domain suite | 191 passed, including localhost HTTP tests |
| Optional AI transport suite | 10 passed |
| Legacy UI helper suite | 4 passed |
| Hosted API, identity and database suite | 11 passed with a disposable PostgreSQL instance |
| React tests | 11 passed, including late workspace responses, history restoration, contributor empty state, retry, dialog focus and compact details |
| TypeScript and Vite production build | Passed |

The React tests use synthetic workspace responses. Live execution against the isolated before and after frontend builds is recorded below. M01 and M02 now have a separate [implementation receipt](m01-m02-results.md).

## ContextQA journey definitions

[Illustrated guide and case links](m00-journey-guide.md) · [Machine-readable capture record](m00-capture.json). See the [live run results and remaining acceptance gaps](m00-acceptance-results.md).
