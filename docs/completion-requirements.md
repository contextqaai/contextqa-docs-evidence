# Completing the documentation lifecycle

The examples must use Layerpath and EkLine themselves. A lifecycle is complete only when real evidence proves the capture, output, change and refresh stages. A plan, fixture, local draft or passing wrapper test does not establish native partner execution.

## Access and decisions

| Need | What must be available | Why |
| --- | --- | --- |
| Product workspaces | Non-Google sign-in to Layerpath and EkLine; permission to create isolated sample drafts | Exercise their real interfaces without modifying existing work |
| EkLine Docs Agent | Enabled account access | Run a real documentation session; account sign-in alone may not enable the Agent |
| Safe target | Dedicated demo workflow with invented data; reachable staging URL if testing sandbox recapture | Real recapture needs an app that the agent can reach and navigate |
| Docs destination | Only the authorized `contextqaai/contextqa-docs-evidence` repo, or an explicitly approved separate contextqaai demo repo | Store selected images and documentation changes without accessing indivatools |
| Repository integration | Existing scoped EkLine connection, or explicit approval for a new limited GitHub App installation | Native PR creation requires repository access; do not silently expand an installation |
| Release source | Real code/release diff or an explicitly labeled controlled content revision | Distinguish observed changes from invented platform updates |
| Publishing decision | Draft/private preview by default; a separately authorized destination for public assets | A shared demo link can expose every included screen |

Never enter Google SSO without specific permission. Never access `indivatools`. Do not buy credits or start a paid subscription for the sample. No scheduled refresh is created by this plan.

## Work remaining by capability

| Capability | Implementation needed | Evidence required to call it complete |
| --- | --- | --- |
| Capture screenshots again | Use the existing ContextQA execution producer or a configured EkLine sandbox; fix viewport, role, locale and test data | The same real task produces readable current screenshots on two captures |
| Link steps to screenshots | Add stable task and step IDs to the capture producer, rather than matching frames by guesswork | Added, removed and reordered steps map correctly; ambiguous mappings are held |
| Explain what changed | Ingest an approved release diff; map affected tasks to docs/tours; preserve human-authored context | Reviewer can trace every proposed edit to source change and screen evidence |
| Visual comparison | Connect a supported visual-diff result or build a bounded image comparison with masking/thresholds | Structural UI changes are detected; timestamps and seeded-data differences do not create excessive churn |
| Redact evidence | Apply tested masks/metadata handling, then inspect screenshots and full video/audio | No secret or personal content survives in approved output; failures block sharing |
| Refresh Layerpath tours | Use its editor/media intake now; confirm a supported API before automating imports or updates | New screenshots replace old scenes; every hotspot and tour branch works after replacement |
| Refresh EkLine docs | Configure its documented screenshot-maintenance workflow and scoped docs repository | A real session creates a reviewed docs/image PR with correct paths and source context |
| Video | Enable recording in the capture producer; finalize the recording, inspect it and select approved output | A playable video of the real task exists and matches the documented version; trace frames alone do not count |
| Hosted iframe | Host selected approved HTML/media over HTTPS with suitable embed headers and access controls | Actual destination renders it, navigation works, and unauthorized users cannot access protected evidence |
| Safe automatic runs | Durable run ledger, duplicate protection, timeouts, cost caps and reconciliation | Retries never silently start another billed run; ambiguous execution stays unresolved until checked |
| Release automation | Release event handler, dependency mapping and review queue | One release produces one scoped draft; no automatic publication or duplicate PRs |

## Prefer native capabilities where they exist

EkLine documents an on-demand screenshot refresh using an enabled Docs Agent, connected docs/images repository and named product sandbox. Its guide also describes recurring refresh, but no schedule is activated here. Validate one on-demand run first. [EkLine screenshot maintenance](https://docs.ekline.io/agent/refresh-doc-screenshots/).

Layerpath documents creating an editable tour from images/video and reviewing its ordered steps. Use that supported intake and editor for the first native example; a platform-specific automated update API has not been verified. [Layerpath first project](https://docs.layerpath.com/get-started/create-your-first-project).

## Practical build order

1. Demonstrate a real manual lifecycle in each native platform, using private sample drafts.
2. Validate one repeat capture and owner-reviewed refresh before adding event automation.
3. Automate the producer and protected artifact delivery; integrate native partner features where verified.
4. Add release-to-document mapping, visual/redaction safeguards and one-shot draft creation.
5. Pilot with a consenting user; measure active author/reviewer time, repeat usage and actual execution/storage cost before deciding pricing.

A hosted general-purpose browser-session service is a separate product milestone. These documentation workflows do not require building that infrastructure first.
