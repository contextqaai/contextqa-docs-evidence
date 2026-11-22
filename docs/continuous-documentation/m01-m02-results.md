# M01 and M02 implementation and acceptance

M01 adds workspace creation, saved setup, subject-bound invitations, member roles and the ContextQA crawl handoff. M02 adds GitHub installation discovery, independent product and documentation scopes, signed event intake and an idempotent source-to-inbox path. Both modules remain in acceptance review. [Operator workflow](m01-m02-operations.md)

## Criterion-level results

| Criterion | Verified behavior | Remaining acceptance |
|---|---|---|
| M01 AC-1 · Resume | PostgreSQL-backed HTTP tests created one workspace on repeated submit, recovered saved settings and rejected a stale revision. GitHub scope reads returned the saved docs directory. | Browser sign-out and return through a customer identity provider. |
| M01 AC-2 · Role changes | The hosted API rejected an editor inviting an admin and protected the last administrator. | Multi-user browser journey in a writable staging tenant. |
| M01 AC-3 · Assigned items | Existing domain and UI checks cover contributor assignment and scoped views. | End-to-end search and artifact access receipts with distinct contributor accounts. |
| M01 AC-4 · Revocation | A removed member’s existing authenticated client immediately lost access on the next API request. | Cross-session browser and artifact checks with real OIDC. |
| M01 AC-5 · Expiration | A rotated code and a code for a different account were unusable. An expired invite returned its own recovery message. JWT expiration and scope tests passed. | Live IdP callback, expired-session recovery and re-login. |
| M02 AC-1 · Deduplication | Four concurrent identical deliveries produced one item. A merged PR for the same push revision mapped to it. An altered payload reusing a delivery ID was rejected. | Real GitHub redelivery in a customer test installation. |
| M02 AC-2 · Source scope | Invalid signatures and unselected repositories were rejected. A push to a different branch was ignored. | Live signed deliveries from the intended installation. |
| M02 AC-3 · Destination scope | GitHub repository discovery and selection were tested with a simulated installation response. The draft PR adapter rejected scope drift and staged the file under the configured documentation directory in a recording command runner. | Operator-authorized PR against a real documentation destination. |
| M02 AC-4 · Revision binding | Intake stored the source revision and attached it to a review item. A hosted guide staging check required actual successful ContextQA exports, matched the workspace and rejected a changed binding. | A new source push followed by independently verified deployment and recapture. |
| M02 AC-5 · Disconnect | The hosted API rejected intake after disconnect and accepted an authorized reconnect. The UI explains what remains installed in GitHub. | Live provider uninstall/reconnect and expired installation credentials. |

## Local verification

All 239 local checks passed: 193 Python domain/CLI tests, 18 hosted identity/API/PostgreSQL tests, 14 React tests, four legacy UI tests and ten offline AI transport tests. The TypeScript/Vite production build passed. GitHub, OIDC and ContextQA tests that substitute a provider are recorded separately from live browser evidence.

An additional test imported a **previously reviewed real ContextQA journey** for the Kan board/list/card guide into a disposable hosted database. It produced one guide change and five media assets. The same import reused the existing item. Changing the expected ContextQA workspace rejected the export. This verifies the guide handoff independently of the new app walkthrough. A separate hosted test verified that a replayed draft-PR request returns its existing receipt without advancing the reviewed item revision or issuing a second GitHub write. The test used a simulated GitHub write. No external PR was opened.

## Continuous maintenance

A push or merged PR on the configured product branch now creates a source receipt and review item. Operators can use verified exports to stage updated how-to guides, then use a separate confirmed command to open the approved documentation PR. Background selection and replay of affected journeys after deployment, automatic editorial drafting, scheduled refresh, and publication verification remain later modules.

## Ship 5 setup walkthrough

A time-limited, read-only synthetic fixture served the real compiled frontend. It held an admin identity and sample API responses. It had no customer login, real repository token or live database. Saved case 201 exercised the UI at 1280 × 720. The fixture served frontend asset `index-Cmiz1mOo.js`. Case 203 loaded the final frontend asset `index-x-1P2AWL.js` and its trace confirms a 390 × 844 CSS viewport.

| Attempt | Ship 5 receipt | Outcome |
|---|---|---|
| Onboarding crawl | Tenant App Details returned requirement 1, runner case 1 and session `22702813-f81c-4138-9395-228f58af3325` | Ship 5 reported completed onboarding and `autonomousCrawlEnabled: false`. The session lookup returned no execution row, and runner case 1 pointed to a historical crawl. There is no fresh autonomous crawl result to cite for this app. |
| Saved discovery through ngrok | Case 201, result 464, step 803 | Failed at the tunnel after the interstitial. The trace shows HTTP 503 and ERR_NGROK_3004 before the product loaded. |
| Saved discovery through the second tunnel | Case 201, result 465, step 804 | Passed. Observed the request and blocker, app discovery form, GitHub repository choices, and organization membership and invite controls. Server-side writes, repository authentication and invitation acceptance were outside this read-only run. |
| Saved navigation and recovery | Case 202, result 466, step 805 | Passed. Restored an inbox item after an empty search, inspected the empty baseline state, and verified sources, health and activity surfaces. |
| Final mobile setup | Case 203, result 467, step 806 | Passed. Loaded the GitHub choices, switched to Members, confirmed the prior success message cleared, and verified the invite form fit without horizontal scrolling. |

The desktop recording exposed a stale status notice when switching from GitHub to Members. The UI now clears section-specific feedback on a tab change, with a React regression assertion. The guide identifies the capture by result so both recorded states are traceable. The mobile result verifies the correction on the final frontend build. The desktop journeys record the preceding build. [Illustrated walkthrough](m01-m02-walkthrough.md)

## Ship 5 credit usage

The available balance went from 14,768 to 14,764 credits during this pass, against the 1,000-credit ceiling. The ledger showed four one-credit web-step charges at 05:32, 05:50, 05:56 and 06:04 UTC on November 22. It showed no autonomous crawl charge for the day at this check. The web-step entries have no run result IDs, so attribution is by time and balance. Earlier M00 runs are outside this window.

## Open provider acceptance item

For Rohit or Shailesh: “How should an already-onboarded Ship 5 workspace start a fresh app discovery for a new client and return its generation job, runner result and artifact IDs? The App Details call returned requirement 1 and case 1, but its session did not resolve to a new execution. Please confirm the supported per-client entry point, how it isolates credentials and how we can correlate the resulting capture to the submitted app and build.”
