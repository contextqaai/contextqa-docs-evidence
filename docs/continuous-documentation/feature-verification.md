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
