# Verify exported walkthrough navigation

This pilot exercises the existing SoFa HTML exporter. The reader can see their position and return to the beginning in one action. It covers the position and restart requirements for exported guides. Fullscreen, branching, tracking and the hosted editor have separate acceptance criteria.

## Frozen reader contract

| ID | Observable outcome |
| --- | --- |
| AC1 | Each section shows Step X of Y and its navigation landmark has the same accessible name. |
| AC2 | Restart from every step links to the first section. Keyboard activation transfers focus there without opening a new document. |
| AC3 | Previous and Next reach only adjacent valid steps. The first has no Previous and the last has no Next. |
| AC4 | A one-step guide shows Step 1 of 1 and only Restart. |
| AC5 | At 320 CSS pixels controls fit without horizontal scrolling. Each link is at least 44 × 44 CSS pixels. Keyboard focus has a visible 2 px outline. |
| AC6 | Navigation works as local fragments with the existing restrictive content policy. Authored text stays escaped. No new service, login or database write is needed. |

## Run with ContextQA

1. Run `python3 examples/walkthrough-verification/build.py /path/to/new-directory` for both revisions in separate checkouts. Serve only their synthetic output to your runner. Bind the three-step URL, one-step URL and checks.html URL in each ContextQA environment.
2. Open checks.html in a ContextQA browser case and assert that the visible text of `#outcome` equals `ALL EXPORT CHECKS PASSED`. Each row displays a separate assertion. The check page uses JavaScript as a test instrument. Both exported readers use native HTML fragments and retain their own content security policy.
3. For a separate real keyboard case open the three-step URL with `#step-3`, press Tab twice and Enter, and assert that the current fragment is `#step-1`. On this fixture the final navigation contains Previous followed by Restart.
4. Run the same checks on the candidate and retain the run ID, terminal result and actual URL. Verify the browser engine from execution evidence before crediting cross-browser coverage. An iframe at 320 CSS pixels exercises reflow. A physical mobile browser, screen reader, visual focus check, performance budget and security assessment require their own evidence.
5. For the app's static example, copy the generated three-step index to `apps/web/public/walkthrough-example.html` and change only its relative logo URL to `/logo.svg`. In the running app, open **Guide library → Try the three-step exported walkthrough**.

The HTML delivery smoke can check the two fixture URLs for 200 and a deliberately missing artifact for 404. These static responses do not exercise a database or establish production availability.
