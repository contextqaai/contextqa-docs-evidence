# Verify a feature and maintain its how-to guide

For each user-facing feature, give the factory two deliverables: a verdict against the feature’s acceptance criteria, and a proposed documentation change grounded in the same ContextQA journeys. A reader may need an accurate guide while the broader module still has open criteria. Track those decisions separately.

## Define the journey before implementation

Give each feature a stable journey ID, a reader role and a task expressed as an outcome. Record the starting data, workspace, feature flags, target build and expected final state. Identify the existing guide and section, or the reader need for a new guide. The module’s example journey is a starting point. Add cases for each independently shipped feature and map every applicable AC to an explicit assertion.

| What to verify | What the factory tests or reviews | Evidence required to close the check |
|---|---|---|
| Business rules | Try the permitted action, a denied or invalid action, and recovery. For writes, check who may act, expected state after reload, and absence of unintended effects on rejection or repeated submit. | Saved ContextQA case and step result for visible behavior. Add API, database or provider receipts for hidden invariants such as one logical write. |
| End-to-end functionality | Start at the user’s normal entry point. Carry the same item across screens or services. Verify the durable outcome from the recipient’s or reader’s surface when the feature promises delivery. | Execution ID, tested revision, item identity and terminal assertion. A displayed “queued” message proves only queueing. |
| Design system and look and feel | Name the component, state and reference in the UX spec or approved baseline. Check typography, spacing, semantic color and text, focus styling, button hierarchy and layout at the affected breakpoints. | Comparable ContextQA frames with the same data, viewport, role and state. Record the specific discrepancy or approved intentional change. Attach measured styles, contrast or geometry for numerical claims. An automated visual difference is a review cue. |
| User experience and accessibility | Complete the task using the offered labels. Exercise keyboard/focus, narrow layouts, pending feedback, errors and recovery where relevant. Verify the user retains their work and can identify the next action. | Step assertions and frames at consequential states. Record a reader walkthrough against the guide-quality rubric for claims about independent task completion. |
| Documentation | Mark the checkpoints that teach the task. Reuse successful role- and build-matched steps and clips. For troubleshooting, use a case that explicitly verifies the expected error and recovery. | Link each procedural section, screenshot and clip to its exact source. Record the proposed disposition, reviewer and delivery state. |

For a backend-only ticket, name the downstream user journey it can affect. Verify the invariant at its authoritative interface and replay that journey when its behavior changes. Record a reason for each inapplicable dimension. Test data, dates and animations may be normalized in visual comparisons. Never mask the control or content under review.

For each public demo link included in a guide, record its exact entry URL, build and intended reader action. Run the installed portal with its normal response headers. In ContextQA, open the link, assert the first visible instruction, act on the primary control and verify the resulting scene or destination. Exercise the form's required-field, successful submission and skip paths. Set the mobile viewport on the case and record the resulting page. A health check covers availability only. Keep separate receipts for the static export, design preview, published player and any downstream lead delivery.

## Record the result

Keep one row per assertion. A ContextQA scenario can supply several rows. Copy this receipt into the ticket or its linked results document.

| Criterion / dimension | Role, state, viewport | Action and expected observable result | Actual observation | Case / result / step or supporting receipt | Verdict and remaining work |
|---|---|---|---|---|---|
| Module AC and named check | Role and fixture | Specific comparison, boundary or state transition | Value or state observed | IDs, build, checkpoint | Passed / failed / blocked / untested / inapplicable with reason |

Record a mismatch as **failed**, a missing prerequisite as **blocked**, and an unexecuted assertion as **untested**. A rerun links back to its original failure. If generated steps are intended for replay, record the independent saved-case execution separately. Review the visual and editorial judgments against their references. Accept the feature when every applicable required assertion has passing evidence and the documentation disposition is recorded. Report module acceptance only when every required feature and cross-feature criterion is covered.

## Maintain documentation when code changes

1. Map the changed source or feature to the affected journey, guide section, images, inbound links and navigation. Bind the candidate journey to the deployed revision. A push can queue the work while deployment is pending.
2. Run the saved happy path with representative data. Capture the decision point, changed interaction and visible outcome. Compare against the last approved guide and its evidence at equivalent checkpoints. Record changed labels, steps, expected results, figures and any prerequisites. Preserve unrelated edits.
3. Choose a disposition below. Record the guide path and version, affected sections, reason, before and after evidence, proposed change and reviewer. A failed run can open a repair item. Keep the last approved guidance available and flag uncertainty against its tested revision.
4. Write for the reader. Include audience, prerequisites, numbered actions using observed labels, expected outcome and verified recovery. Place figures next to the matching steps with alt text. Include a short clip when motion or a multi-step interaction helps. Record case/result/step IDs, source frame or clip time range, build, role, viewport and file checksum. Inspect the exported media for legibility and private data.
5. Preview the complete change set. Verify navigation, links, assets and reader access. Route it through the existing approval and delivery flow, then verify the destination and record its published revision. Bind approval to the exact content and media. Upstream drift reopens review.

| Disposition | Trigger | Required outcome |
|---|---|---|
| Create | A new supported task has a passing journey and no existing guide serves that reader need. | Draft a guide from verified steps and figures, link it from its intended entry point, and check the preview. |
| Update | A supported task, label, prerequisite, outcome or useful illustration changed. | Diff the affected sections and figures. Reuse valid content and verify updated steps against the candidate. |
| Retire or delete | A confirmed product decision removes the supported task for the documented audience/version. | Verify the old entry point on the candidate, the applicable role/flags, and the replacement path when available. Propose archive, redirect or explicit deletion. Review inbound links, navigation, versions and shared media. Preserve the prior approved revision and require approval of the exact removal before delivery. |
| No change | Equivalent checkpoints still support the current instructions and figures. | Attach the fresh verification receipt. Leave the guide version and assets intact. |
| Needs investigation | A case fails unexpectedly, a feature flag or permission hides a control, or the source listing is incomplete. | Record the blocker and last verified version. Resolve the ambiguity before proposing removal or publishing new instructions. |

## Worked decision for M00

The reader’s task is to find a request and inspect its evidence. Before case 196 / result 459 opened in **Review inbox**. After case 199 / result 460 opened in **Workspace overview**, where **Requests needing attention** exposed both the title and outstanding question. The same editor, request and 1280 × 720 viewport make the landing states comparable. The resulting guide disposition was **update**. Change the entry steps and overview screenshot, retain the evidence-inspection task, and keep the existing inbox in the instructions. Result 463 separately supports mobile recovery and article selection. [Illustrated guide](m00-journey-guide.md) · [Evidence manifest](m00-capture.json)

The candidate overview frame shows an active Overview navigation item and a textual “Needs evidence” badge. The mobile frame shows a single-column review with a labeled article selector, a textual blocker and a disabled finish action. These observations support specific visual checks. Rendered contrast, token dimensions, keyboard menu traversal and independent learner completion still need evidence. Database-backed tests cover approval invalidation, while browser verification of a writable conflict remains open. **M00 stays in review.** [Criterion-level report](m00-acceptance-results.md) · [UX reference](ux-spec.md)

## Optional ContextQA API and database checks

For a change to validation, authorization, idempotency or stored state, select the optional checks that expose the rule. Record their target workspace, deployed revision, expected outcome and run/step result. A case can use a positive read and a rejected write against the same fixture. For export, run the browser action, then check the approved guide head, media references, owner approval and export timestamp with a read-only database login. Use the client staging database and a scoped verification view.

Record a missing private route or login as pending. An HTTP step that queries fixed SQL establishes the returned assertions. A native Database step additionally tests the runner's database connection. Only the browser capture supplies the product screenshots and videos used in the guide. [See the documentation app's test results](platform-acceptance.md).

## Close a failed PR check

For each failed or unexpectedly passing case, preserve the first receipt, expected behavior and spec revision. Verify the preview SHA, prerequisite, fixture and signed-in role. Compare the same journey on the base and candidate where attribution is unclear. Fix the product when it violates the contract. Fix the test when it selects the wrong control or starts on the wrong screen. Fix the environment when its identity, data or provider binding prevents the assertion. Keep positive and negative integration scenarios distinct.

Replay the original assertion after a product or fixture repair. For a test repair, record the before/after steps and the observable business outcome they still enforce. On every new commit run impacted cases again against the matching preview, including neighboring paths. Report each terminal case ID, actual outcome and unresolved dependency. A blocked provider write needs its own live receipt before release.

## Continuous verification for each feature

The factory owns the next action after the owner approves a feature. On a new specification, changed PR head, deployed preview, configuration change, failed run or merge, resume the feature's verification record. The hourly worker reconciles missed events. A quiet hour with current evidence starts zero runs.

| Stage | Trigger and action | Exit condition |
|---|---|---|
| Requirements | Submit the owner-approved spec to ContextQA. Record its revision, dependencies, role, fixture, expected positive and negative outcomes and design reference. Crawl where entry points are unknown. | Every acceptance criterion has a check or an explicit owner decision pending. |
| Small checks | Run one deterministic assertion at a time for each changed rule. Include an invalid input, boundary value or wrong role wherever relevant. | Observable state, response or record matches each expectation. |
| Contracts | Run affected API and read-only database checks, including failure and recovery. | Server response and persisted state agree. |
| Journeys | Exercise the normal user entry point, primary action, persistence or destination, return path and recovery. Record desktop, keyboard and actual mobile viewport where applicable. | The user reaches the specified outcome in each supported context. |
| Specialist coverage | Evaluate all eleven phases. Run applicable compatibility, performance, security control, accessibility, integration and application security checks. Record rationale for each inapplicable phase. | Every required row has a current result and evidence. |
| Change impact | On a new PR head, revised requirement, fixture, browser target or deployment, recalculate affected tests and reconcile capped selections. Execute approved additions and updated tests. Record the disposition of retired cases. | The tested revision, selected cases and results reconcile. |
| Repair | Classify failures using result, trace, expected behavior and actual role or viewport. Correct the product, test, fixture or infrastructure at its source. Preserve the original failed result. Replay the smallest failing check, its affected journeys and impact cases. | The original requirement passes on the repaired build. Unknown outcomes stay open. |
| Release and guide | After an authorized merge, recheck the deployed revision and reader path. Use the successful ContextQA evidence for the guide. | All required rows pass for the stated release scope, or the report records NO-GO and the outstanding rows. |

Keep the verification record outside the source revision it describes. Record the feature, spec revision, deployment identity, dependency versions, expected cases, environment, browser and measured viewport. Journal a run intent before launch and attach the returned execution ID. After interruption, reconcile Ship 5 history before launching again. Only one worker owns a feature's active execution. Reuse a passing receipt when its tested inputs and dependency revisions are still valid. Repeated identical failures require diagnosis or an owner decision, while independent checks continue.
