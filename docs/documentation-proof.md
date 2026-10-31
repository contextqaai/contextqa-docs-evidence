# Documentation proof: Kan

## Intended acceptance

For an authorized Kan staging workflow: execute with the requested ContextQA Max mode; collect actual step screenshots and recording; create a reviewed guide with capture date/version and callouts; rerun against a known deployed revision; compare and propose an update. Use `nigharsh/kan` pull requests to identify affected guides. Use ContextQA exclusively for workflow execution and capture. Do not use browser automation or a browser preview as a substitute for hosted execution or label the staging app with a PR SHA without deployment evidence.

## Implemented in this revision

- `capture-context WORKSPACE --file context.json`: review-bound operator labels for workflow, version, capture time, environment, method, runner and optional commit/PR. Labels are explicitly not independent attestation.
- `annotate WORKSPACE --step N --file annotations.json`: percentage-based screenshot rectangles and numbered captions. HTML renders the callouts; Markdown links to that annotated HTML and preserves the original screenshot. It does not burn annotations into the bitmap.
- `fetch-media`: selected provider-reference retrieval with an exact reviewed public host, no token forwarding, no redirects, bounded size and media checks. Downloads do not auto-attach or approve.
- Compare ignores changing execution result IDs while preserving them in the report. It still compares text/media identity, not semantic behavior.
- `integrations/kan/docs_request.py`: maps complete PR changed-file lists to known documentation workflows, including renamed paths. A supplied deployment SHA must match the PR head. Request generation is not capture completion.

Example annotation (replace the media ID with one attached to that step):

```json
[{"media_id":"ACTUAL_SHA256","x":30,"y":25,"width":35,"height":10,"label":"Enter a descriptive card title"}]
```

Example context:

```json
{"workflow_id":"kan-create-card","app_version":"staging revision not yet verified","captured_at":"2026-10-31T04:00:00Z","environment":"Kan QA","capture_method":"ContextQA API results","runner_mode":"must be verified against the tenant"}
```

Any change to labels or annotations invalidates the previous review receipt.

## Earlier October 30 observations (superseded where noted)

See [the latest MCP and receipt audit](verification-2026-10-30.md). The latest continuation confirms ship-5 and records a real Kan login-blocked execution (case 174/result 371). The earlier tenant mismatch is resolved; the complete workflow remains unverified.

### Earlier observations

- The supplied ContextQA token successfully read bounded pages of plans, cases and results. Token values were not saved in this repository.
- ContextQA MCP is registered locally but not exposed as tools to this chat. The user is reconnecting it.
- The tenant UI uses `Expert (Recommended)` in organization AI configuration; the create dialog shows Smart/Fast/Strict. The inspected token schema has EXPERT but no MAX enum. Max equivalence has **not** been established. No organization settings were changed and no hosted execution was started.
- Earlier browser reconnaissance created an isolated demo board/list/card. The user subsequently required ContextQA only. The preview server was stopped; those private images are excluded from acceptance and no browser preview is a deliverable. A fresh ContextQA run is still required.
- Actual PR #18 at head `a0d0587a5f1fe13c0c132e235c6c7148825c2fe5` maps to card/checklist documentation requests. Deployment matching remains unverified.

## Remaining acceptance gates

1. Workspace identity is verified as ship-5/version 1. Resolve Max availability; actual execution reports EXPERT.
2. Resolve the observed magic-link login blocker using an authorized ContextQA auth profile or password-enabled QA target. Saved password credentials alone did not complete the current login flow. Never place credentials in GitHub artifacts or prose test scenarios.
3. Run a bounded selected workflow with screenshots/video enabled at case level. Record the accepted ID, actual terminal outcome, mode evidence and actual provider usage if available.
4. Retrieve and visually review selected real media, then export. Missing video remains missing; a slideshow is not a live recording.
5. Obtain a deployment tied to the selected PR head, repeat the same workflow, and review the comparison. A change-request trigger alone is not continuous documentation maintenance.

The repository is not yet proven as a complete unattended documentation product. Native documentation publication, screenshot/audio redaction automation, narrated video editing and semantic release interpretation are outside this patch.
