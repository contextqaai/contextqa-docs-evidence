# PageLoop behavior and the ContextQA implementation

Research checked 2026-11-19 through official documentation, official product material, a video transcript and Treg extraction. This is a reconstruction of publicly described behavior, not access to PageLoop's private implementation.

| Observed behavior | Source | ContextQA implementation/status |
|---|---|---|
| Detect product changes, draft documentation, review in Inbox, then publish | [How PageLoop works](https://docs.pageloop.ai/guides/how-pageloop-works) | Persistent normalized events → impact mapping → article proposals → review → explicit draft delivery |
| Per-change accept/ignore/undo, editable articles, questions and activity | [Review an inbox item](https://docs.pageloop.ai/guides/review-inbox-item) | Implemented review controls, Markdown editor, assignment, questions and audit activity |
| Scheduled or merged-PR workflows, test runs and pause controls | [Workflows](https://docs.pageloop.ai/guides/workflows) | Signed GitHub event normalizer and local CLI exist; hosted receiver, scheduler and pauseable workers are not implemented |
| Grouped changes, drift checks and explicit delivery | [Change sets](https://docs.pageloop.ai/guides/change-sets) | Exact article baselines, review versions, hash-bound approvals, reviewed ZIP and explicit text-only draft-PR adapter |
| Screenshots from configured application workflows with capture restrictions | [Automated screenshots](https://docs.pageloop.ai/guides/automated-screenshots) | Reuse ContextQA executions and reviewed media exports; no fabricated screenshots or universal login automation |
| Segment a recording into feature-specific documentation updates | [Video-to-documentation product article](https://www.pageloop.ai/blog/how-to-turn-video-into-documentation) | Validated transcript-segment intake; ASR, frame selection and a recording extension are not implemented |
| Record workflow context, edit/annotate and publish | [Official demonstration](https://www.youtube.com/watch?v=RyEjhQ0vcWs) | Transcript reviewed; no claim of frame-by-frame video verification. Existing Docs Evidence supplies reviewed step/media export |

The reusable product loop is change detection → grounded proposal → execution evidence → human review → controlled delivery. The main ContextQA advantage is its existing test context: prerequisites, test data, environment, execution results and media can support the article rather than treating a successful navigation as proof of the entire workflow.

A PR can support a source-derived draft without proving deployed behavior. A terminal test run can still fail. A passing unit test does not prove a browser workflow. The Kan request displays all three distinctions.

The user specifically requested Kan PR #15 as real context, so `examples/kan-pr15` is a labeled historical snapshot, unlike the synthetic account-free test fixtures. No credentials, signed artifact URLs or customer media are included. The source proposal paths are new proposed articles, not claims that those pages already existed in Kan.
