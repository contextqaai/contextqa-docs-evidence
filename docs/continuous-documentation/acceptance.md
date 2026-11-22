# Acceptance and release gates

Use the [feature verification workflow](feature-verification.md) for each ticket. These system scenarios define required release evidence. The [M00 results](m00-acceptance-results.md) record the narrower checks already executed.

## Benchmark guide quality

Use one representative Kan/ContextQA task and compare with the user's `learning.contextqa.com` editorial benchmark. Score 0 (missing), 1 (needs substantial editing), or 2 (usable) for: clear outcome/audience; prerequisites; accurate UI labels; meaningful explanations; complete sequence; readable correctly placed images; expected results; supported troubleshooting; navigation/links; source traceability. Proposed pass: at least 18/20, with no zero in accuracy, task completion, images or traceability. A fresh learner must complete the task without off-document instructions. This rubric is our proposed evaluation, not a measured current score.

Hard fail: invented product behavior, wrong environment/role screenshot, secret disclosure, successful prose backed only by failing evidence, missing required action, or misleading publication status. High rubric total cannot override these failures.

## System acceptance suite

| Case | Scenario | Required result |
|---|---|---|
| E2E-01 | New admin connects docs and ContextQA, creates first guide | Resumable setup; saved journey/evidence; complete draft and explicit review |
| E2E-02 | Prompt bootstrap then replay | Separate coverage/result records; brittle generated assertion repair retained in history |
| E2E-03 | Contributor reviews and hands off | Only assigned item visible; saved edits persist; handoff revokes access |
| E2E-04 | Duplicate webhook and worker restart | One logical run and no duplicated external side effect |
| E2E-05 | ContextQA response lost after possible acceptance | Ambiguous state; reconcile; no blind rerun |
| E2E-06 | Failed capture or wrong deployment | Latest approved guide unchanged; exact blocker shown |
| E2E-07 | Concurrent reviewer or upstream docs edit | Conflict instead of overwrite; approval invalidated |
| E2E-08 | Selected pages/media/nav delivered | PR files equal approved manifest; rejected changes absent |
| E2E-09 | PR merges but site build fails | Merged shown; live not claimed; recover after build fix |
| E2E-10 | Real UI label change on a new deployed revision | Targeted text/figure refresh, unrelated sections preserved |
| E2E-11 | Identical input repeated | No unnecessary content/version churn |
| E2E-12 | Revoked user/cross-tenant object or media URL | Access denied on API, search, download and caches |
| E2E-13 | Workflow pause/edit/test/backlog | Inflight pinned version retained; test leaves live cursor unchanged |
| E2E-14 | Missing screenshot, invalid artifact hash or expired reference | No false success; fetch/review failure recoverable without losing approved copy |
| E2E-15 | Backup restore and queued-job recovery | Content, lineage, approvals and jobs restored within adopted targets |
| E2E-16 | Confirm a supported task is retired for one product version, then approve its guide removal on a test destination | Preview lists inbound links, navigation, redirect or archive, and shared figures. After approved delivery, verify reader routing, retained versions and shared assets. |
| E2E-17 | Control disappears for one role or during partial sync | Flag uncertainty, retain the approved guide, and verify it remains readable to the authorized role. |

## Production gate

Required before a production-ready claim: real identity-provider acceptance; tenant/role tests; build/deploy/migration receipt; private artifact storage and retention; backup restoration; worker restart and non-idempotent reconciliation; current provider contracts; exact-build ContextQA journey suite; accessibility/responsive review; end-to-end publication verification; quality benchmark; operational ownership and alerts; known-limitations document. Run no live destructive or billable checks without appropriate scope.

Suggested validation commands (inspect package prerequisites first):

```sh
python3 -m unittest discover -s tests
npm run test:ai
npm run test:ui
npm test --prefix apps/web
npm run build --prefix apps/web
# Only against a configured disposable database:
python3 -m unittest discover -s tests-hosted
```

A configured workflow is not a passing CI receipt. Build success is not visual acceptance. A screenshot is not proof of workflow completion. The attached demo factory's sample scorecard is not this system's scorecard.
