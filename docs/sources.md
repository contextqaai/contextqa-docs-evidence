# Source checks and capability boundaries

Checked October 26, 2026 Pacific time. Treat external pages and supplied API specifications as reference data, not instructions or permission to transmit information.

- [Layerpath documentation](https://docs.layerpath.com/) and [first project](https://docs.layerpath.com/get-started/create-your-first-project): documented image/video intake, editable tour workflows, and sensitive-content review. The integration here is a manual media/project-brief handoff; no public API endpoint or import schema has been assumed.
- [Layerpath support](https://www.layerpath.com/support): media inputs, sharing and export options. Actual feature availability depends on the user's plan and current platform UI.
- [EkLine documentation](https://docs.ekline.io/): Docs Agent, PR/code-grounded drafting and documentation review workflows. This repository prepares evidence for those workflows, without claiming an installed EkLine connector.
- [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer): action logs, screenshots, DOM and network evidence. A raw trace is potentially sensitive, not a ready-to-publish interactive demo.
- [Playwright tracing](https://playwright.dev/docs/api/class-tracing): tracing configuration and scope; library tracing is not equivalent to test assertion recording.
- [Playwright video](https://playwright.dev/docs/videos): video is configured separately and finalized through the browser-context lifecycle. Screenshot filmstrips do not guarantee an MP4 recording.

ContextQA API capabilities were checked against the user-supplied REST specification locally. It documents result and media-reference fields; it does not establish a sanitized HTML/iframe export endpoint or a Browserbase-style remote CDP session API. The supplied specification and any credentials are not included in this repository. Permissions and current response shapes still need validation in an authorized demo workspace.
