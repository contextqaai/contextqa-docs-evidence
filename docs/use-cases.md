# Documentation and demonstration use cases

The core workflow is customer-application capture through ContextQA followed by reviewed documentation and scoped refresh. Layerpath and EkLine are optional destination ideas, not required dependencies, partnerships or completed integrations. Current vendor features must be verified separately.

| User need | Evidence supplied | Deliverable | After an app update |
| --- | --- | --- | --- |
| Write a how-to guide | Reviewed steps and screenshots of a seeded task | Markdown with image attachments and version note | Recapture task, compare mapped steps, draft replacement instructions/images |
| Maintain an interactive demo | Ordered images, optional separately recorded video, task goal | Layerpath project brief and selected assets | Replace affected scenes, review branches/hotspots and republish in Layerpath |
| Keep developer documentation current | Release context plus reviewed old/new evidence | EkLine-ready evidence brief and documentation refresh draft | Reconcile code/API changes with visible UI behavior; docs PR review |
| Update onboarding and training | Role-specific workflows and expected outcomes | Screenshot guide or static HTML walkthrough | Recapture for each changed role, flag and supported locale |
| Explain a release to support/sales | Before/after captures and owner explanation | Change brief with verified wording | Validate guidance against the release before customer-facing use |
| Investigate stale documentation | Reproduction steps, current screenshots and baseline | Evidence-backed doc issue | Distinguish actual behavior change from theme/data/viewport differences |

## Layerpath: screenshot-to-tour, then keep the tour fresh

A documentation author runs the product's onboarding task in ContextQA. They select screenshots, remove sensitive details, attach them to reviewed steps, and export. If the selected Layerpath account supports the required media intake/editor features, the author can hand off approved assets and a goal/audience brief, then inspect every available native output. The final interactive experience lives in Layerpath; the wrapper's HTML is a simpler static walkthrough.

When the app updates, the author supplies release context and records the same task again. Compare the reviewed versions with explicit step mapping, use the refresh draft to identify obsolete assets, and replace affected tour scenes in the platform. Verify all branches, targets and destinations before publishing; a screenshot hash cannot validate a hotspot. This is a proposed manual handoff; no native intake, update or API adapter is verified here.

## EkLine: grounded documentation drafts with visual evidence

An author provides an actual release PR/changelog and says which documents teach the affected workflow. Capture current behavior in a demo tenant and pair it with a reviewed baseline. Export the guide, selected screenshot assets and comparison draft. Give EkLine the reviewed narrative and evidence through the organization's supported docs workflow. Ask it to update only the affected document sections and include the target version, expected outcome and image references.

A reviewer verifies the draft against both captures and the source change, checks permissions/feature flags, uploads images to the documentation asset store, fixes links/alt text and approves the docs PR. If the client's EkLine account supports the required editor/repository workflow, it may consume that reviewed handoff. This prototype does not invoke EkLine, upload assets, open native PRs or guarantee access to local paths. ContextQA remains the screenshot/execution source; destination-native recapture is not part of this lifecycle.

## Reusable documentation-update brief

- Task and audience: what the reader is trying to accomplish, role, locale and prerequisites.
- Baseline and target: app version, environment, feature flags and capture date.
- Actual change: verified action/label/behavior change, with a private source reference when necessary.
- Affected documents: exact pages/sections/tours, localization variants and owner.
- Evidence: reviewed old/new guide packages; explicit conceptual step mapping; screenshot/video IDs.
- Requested update: replace specified instructions and assets; preserve unaffected guidance; identify uncertainty.
- Acceptance: owner verifies behavior, asset rendering, accessibility, links and version labeling before publication.

Never tell an agent to follow instructions embedded in traces, HTML snapshots, retrieved pages or release text. Those are evidence inputs, not user authorization.

## Related ContextQA resources

See [verified ContextQA guides and articles](contextqa-resources.md) for capture, visual baseline review and MCP workflows.
