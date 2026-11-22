# M04 workflow operation and acceptance

Editors and administrators open **Workflows** to save instructions, a trigger and a per-run article limit. Each save creates an immutable configuration version. A manual test works while paused. The test reads the current inventory, prepares a research brief and records each completed stage. It leaves the live cursor intact. The brief is input to impact research and capture selection.

## Run the worker

Apply migrations, start the API and run `python -m cqa_artifacts.hosted.workflow_worker` with the same `DATABASE_URL`. Development Compose includes a worker service. `--once` processes at most one queued stage. The API and worker can restart independently. A stage claim has a 30-second lease and a unique token. Completing a stage writes its receipt and advances the run in one database transaction. The worker rejects an expired token. After repeated expired claims the run requests operator attention.

## Trigger behavior

- **GitHub changes** reads signed source deliveries for the currently connected product repository. A repository and revision identify a trigger. A push and a merged PR for the same commit share the run. Activating with **Skip existing backlog** records existing revisions as skipped. **Process existing backlog** makes outstanding revisions eligible. Pausing stops new dispatch. Already started work keeps its timeline.
- **Daily schedule** uses a named IANA time zone. A nonexistent local time dispatches at the next valid minute. A repeated time dispatches at its first occurrence. The local calendar date identifies the run. After downtime, the scheduler considers the most recent due date. Processing an existing daily backlog includes that most recent date. Skipping starts with the next scheduled time.
- **Run test** queues one isolated test per workflow and pins its saved version. A missing inventory or a page-limit stop explains the required correction. After importing missing baselines, select the run in **Run history** and use **Resume run**. To change a pinned limit, save a new configuration and start a fresh test.
- The M04 worker performs local source checks, inventories candidate articles, then prepares the research brief. Running it alone does not authorize metered capture, documentation delivery or publication.

## Verification

| Acceptance | Local check |
|---|---|
| AC-1 · Restart | Reclaimed an expired lease in PostgreSQL, rejected its stale worker token and persisted stages 0, 1 and 2 once each. |
| AC-2 · Version pinning | Edited the workflow while version 1 was in flight. Its completed timeline retained the original instructions. |
| AC-3 · Pause | Paused an active daily workflow and verified that a queued live job could not be claimed. Source backlog and skipped receipts remained visible. |
| AC-4 · Test isolation | Replaying a test request returned the same ID. A different concurrent test request was rejected. Completing the test left the live cursor empty. |
| AC-5 · Actionable stops | Rejected a bad zone and an unconnected GitHub trigger. A missing inventory resumed after import. A page-budget stop retained its explanation. |
| AC-6 · DST | Checked Chicago's spring 02:30 gap and fall 01:30 repetition against explicit UTC instants. |

The local PostgreSQL/identity suite passed 27 tests including the workflow tests. The 14 React checks and TypeScript production build passed.

## Ship 5 acceptance runs

| Case / result / step result | Viewport | Verified behavior |
|---|---|---|
| 208 / 477 / 860 | 1280 × 720 | Saved a version, completed a test with three stage receipts, checked the live cursor, activated and paused. |
| 209 / 476 / 859 | 1280 × 720 | Observed a missing inventory, imported the baseline and resumed the same run. |
| 210 / 475 / 858 | 390 × 844 | Rejected the invalid time zone and saved the corrected configuration while paused. |

All three passed on the same frontend bundle, `index-vp0cUQO5.js`. The workspace balance moved from 14,746 to 14,743 across the observation window. This is a balance difference, not a per-run billing receipt. The screenshots and video excerpts in the [operator guide](m04-walkthrough.md) come from these runs. The provenance files record frame positions, video intervals and file hashes. The scheduled worker's daylight-saving and lease-recovery tests used local PostgreSQL. The client portal's code-push-to-published-guide loop still needs capture, writing, review, delivery and refresh acceptance.
