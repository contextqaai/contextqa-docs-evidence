# M00 acceptance results

**Release decision: keep M00 in review.** ContextQA exercised the compiled React application through ngrok against an isolated, read-only synthetic workspace. The before and after runs used the same editor, seeded request and article proposals. A separate local suite exercised the real hosted API against disposable PostgreSQL. These layers establish different parts of the five acceptance criteria.

The [illustrated guide](m00-journey-guide.md) contains the observed user steps, stills and clips. The [capture manifest](m00-capture.json) binds each result to the corresponding build, environment, step result and artifact hashes.

| Journey | Ship 5 case | Result | Actual CSS viewport | Check |
|---|---|---|---|---|
| Before · review a request | [196](https://ship-5.contextqa.com/td/cases/196/steps) | 459 · SUCCESS | 1280 × 720 | Landed in Review inbox, opened the request, verified both evidence headings, returned to inbox. |
| After · review the same request | [199](https://ship-5.contextqa.com/td/cases/199/steps) | 460 · SUCCESS | 1280 × 720 | Verified Workspace overview and Requests needing attention, then completed the same review path. |
| Tablet · inspect and dismiss details | [197](https://ship-5.contextqa.com/td/cases/197/steps) | 461 · SUCCESS | 1024 × 768 | Selected Rename a card, inspected Delivery checklist, closed the panel and verified the selection. |
| Desktop · cancel with keyboard | [198](https://ship-5.contextqa.com/td/cases/198/steps) | 462 · SUCCESS | 1440 × 900 | Opened the request form with Enter, cancelled with Escape, verified opener focus and the original queue item. |
| Mobile · reject, recover and inspect | [200](https://ship-5.contextqa.com/td/cases/200/steps) | 463 · SUCCESS | 390 × 844 | Invalid token hid the request. Valid sign-in restored access. Selected the second article, checked its path before and after inspecting details, and verified reachability on this screen. |

All five executions passed. Each result covers one provider-scored scenario containing multiple browser actions. The initial browser page in the mobile trace used a different layout width. All 2,050 snapshots at the fixture origin used 390 × 844.

## Acceptance by criterion

| M00 criterion | Evidence obtained | Remaining release check |
|---|---|---|
| AC-1 · Responsive actions and overflow | **Partial.** Tablet details, desktop intake and mobile article review passed. Mobile included an explicit horizontal-scroll reachability check. | Measure page width against viewport width and exercise all primary actions at 390, 1024 and 1440 px. |
| AC-2 · Workspace isolation on switch | **Passed locally.** Switching cleared old content and ignored a deliberately late response. PostgreSQL tests covered tenant isolation. | Record the switch in a browser with two workspaces and delayed reads. |
| AC-3 · Failed and empty states | **Passed locally, partial live.** Local tests exercised failed discovery, retry and the first-request action. Mobile showed the rejected credential error, concealed the request and recovered on valid sign-in. | Record a transient read failure, successful Retry load and first-use action in an empty workspace. |
| AC-4 · Keyboard navigation and focus | **Partial.** Enter opened the form. Escape closed it and focus returned to its opener at desktop width. | Verify keyboard-only menu opening, traversal, dismissal and focus return in compact navigation. |
| AC-5 · Review, save and approval invalidation | **Passed locally, partial live.** Local tests covered exact saves, rejected-save retry, stale revisions and invalidated approval. Ship 5 verified review navigation and preservation of article selection. | Capture a writable staging journey that saves an edit, exercises a conflict, and rejects delivery against an invalidated approval. |

## Credits

The approved ceiling was 1,000 credits. The observed Ship 5 balance changed from 14,773 to 14,768. The usage ledger showed five one-credit web-test charges during this window. Its entries omit result IDs, so the balance comparison is tenant-level.

## Independent local checks

- **12 React tests passed.** Coverage includes failed discovery and retry, first-use actions, switching scopes with an old refresh in flight, history restoration, focus return, contributor controls, and preservation of the edited draft after a rejected save. The new retry test verifies the exact text and version are submitted on retry.
- **23 review-domain tests passed.** These exercise successful review and approved delivery, edits invalidating approval, stale revisions, rejected unreviewed delivery, evidence blockers and assignment rules.
- **11 hosted tests passed against disposable PostgreSQL.** These exercise tenant isolation, membership revocation, transaction/reconnect behavior, a complete persisted delivery, stale decisions and rejected requests to override failed evidence.
- TypeScript type-check passed. The new regression test is a test-only change against the candidate application.

## Continuous documentation status

These run receipts and media were used to update this guide in this acceptance pass. M00 provides the workspace and review UI. Automatic updates on a code push require the GitHub event intake (M02), durable jobs (M04), impacted journey capture and drafting (M06/M05), reviewed delivery (M07–M09) and selective refresh (M10). The release demonstration must include a changed UI, an unaffected guide and a failed capture. See the [build order](roadmap.md).
