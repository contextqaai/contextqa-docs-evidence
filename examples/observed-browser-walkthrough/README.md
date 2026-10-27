# Observed local browser walkthrough

Captured October 27, 2026 from a freshly installed ContextQA Browser Cloud loopback demo, with its default Chromium sandbox enabled. All page data is invented. This is an actual browser capture and installed-package export, not a mocked screenshot or a live ContextQA SaaS / Layerpath / EkLine run.

1. Open the companion local Browser Cloud console and select **Start demo session**. Capture/download a screenshot of the initial “No project created yet” state.
2. Set **Text to enter** to `Documentation guide — controlled revision B` and select **Run demo task**.
3. Select **Read page text**. Confirm the exact observed text `Created: Documentation guide — controlled revision B`. Capture/download a second screenshot.
4. End the session and download the finalized video. Raw video/trace are intentionally excluded from this repository example.
5. Inspect screenshots for private information and confirm rights; attach only approved media to the evidence workspace. Review and export.
6. Compare the baseline and completed-state exports using explicit step pairing. This is a controlled task state change in the same app build, not an application release.

View [after guide](export-after/guide.md), [HTML guide](export-after/index.html), [baseline](export-before/guide.md), [comparison](change-review/refresh-draft.md) and [machine-readable changes](change-review/changes.json). Serve this directory on loopback to inspect HTML/images; opening an HTML file from GitHub source does not host the walkthrough.

The installed Python package produced the exports. Both 1280×800 screenshots were visually reviewed and successfully rendered. One paired step changed; changing the private workspace after approval correctly blocked another export. The independent real-browser API smoke also asserted its result, downloaded screenshot/video/trace and rejected an invalid download credential. See [repeatable testing guide](../../docs/real-testing.md).

For real product documentation, replace the invented task with an explicitly authorized staging workflow, maintain role/viewport/locale/test data, record an actual release diff, recapture, review, compare and approve. Do not label a failed or evidence-incomplete run “verified.”
