# UI, design and interaction specification

All layouts below are proposed ContextQA designs. Public guide text establishes reference behavior, not exact pixel measurements. No authenticated Pageloop UI was inspected in this task.

## Information architecture and screen contract

Use workspace-aware routes under `/w/:workspace/`. These are proposed routes, not current routes.

| Screen | Main content and controls | Required non-happy states | Modules |
|---|---|---|---|
| `/setup` | Company/product identity, docs destination, repo/branch/root, ContextQA binding, first task; resumable checklist | Permission denied, partial setup, failed sync, expired auth; optional steps skippable | M01–03, M06 |
| `/home` | Needs your answer, ready to review, running work, latest published updates; primary Create guide action | First-run empty with next step; offline; no assigned work for contributor | M00, M01, M07 |
| `/inbox` | Open/Assigned/Resolved/Archived; ID/title/source/priority/assignee/counts; search and bulk selection | No results, partial load, selection cleared on filter change, per-item bulk failures | M07 |
| `/inbox/:id` | Affected-page tree; Changes/Article/Evidence/Activity; reasons; saved state; handoff/delivery | Needs input, active run lock, missing capture, stale revision, read-only delivered version | M05–09 |
| `/runs/:id` | Stage timeline, scope, sources, capture/replay, coverage, outputs, cost/usage when known | Queued, delayed, needs input, failed, ambiguous acceptance, no changes, superseded | M04, M06 |
| `/knowledge` | Searchable tree, versions/change-set selector; page/folder actions | No docs, incomplete sync, inaccessible source, invalid navigation | M03, M08 |
| `/knowledge/:page` | Visual/source editing, metadata, diff, citations, media drawer, save/preview | Unsaved, saving, save failed, concurrent edit, unsupported MDX, generated page read-only | M08, M14 |
| `/workflows` | Draft/live/paused/attention groups; name, trigger, last/next run | No workflows; disconnected dependency; exhausted budget | M04 |
| `/workflows/:id` | Instructions and Runs tabs; trigger form, timezone, scope references, test/activate/pause | Invalid fields, unsaved edits, backlog choice, active old version, skipped test | M04 |
| `/integrations` | Search/category cards; connection state; configured scope; role assignments | Connected but incomplete, needs reconnecting, provider unavailable, disconnected | M02, M12 |
| `/capture` | ContextQA workspace/environment, saved journeys, roles, target deployment, allowed actions, capture requirements | Missing credential reference, login failure, infrastructure failure, stale definitions | M06 |
| `/health` | Coverage gaps, stale references, failed refreshes, broken links; actions and check scope | Unknown accuracy shown explicitly; failed scan; outdated result | M10 |
| `/settings/members` | Members/invites, role, status, invite/resend/deactivate controls | Last-admin guard, expired invite, wrong workspace, denied role change | M01 |
| `/settings/writing` | Product context, tone, protected terminology, template examples and annotation palette | Invalid fields, overlapping templates, deleted example, unsaved edits | M05 |
| `/settings/connections` | Assistant identity, scope, site access, created/last-used time, revoke | Revoked, expired, role reduced, unsupported capability | M11 |
| `/settings/publishing` | Destination, branch/root, sync/build receipts; later domain/version/reader access | Drift, partial delivery, pending DNS/TLS, failed build; public/protected status | M09, M13 |
| `/assets` | Later: release notes, training, demo and sales content with dependencies | Source stale, pending owner review, failed export | M16 |

## Review layout and interactions

Desktop: persistent navigation at left; compact page list inside review; central document/diff gets most width; source/reason panel on right. At 1024 px use a collapsible evidence drawer. At 390 px use a page selector and one content column, with a reachable action bar that never covers the last paragraph. Do not squeeze three columns onto mobile.

Each change card identifies operation, affected page/section, before/after, reason, evidence and decision. Distinguish deletion from missing preview. Article preview must support a clean accepted-result view. Item-level Accept all and page-level Accept all have different labels/scopes and confirmations. Selecting an item is not opening it. Keyboard access must reach all choices without drag-and-drop.

Question rounds show the fact needed, the affected decision, allowed answers and source context. Save partial answers without resuming. Submit the round once; show answered-by and continuation state. Proposed rule: unknown product permissions or claims cannot be converted into confirmed facts by an agent-default shortcut.

Delivery modal shows destination, included pages/assets/navigation, approved revision, exact operation and remaining blockers. Primary action says Create draft PR, Update PR or Publish to [provider], never an ambiguous Finish. PR created, PR merged and site live are separate timeline events. Main app must never label a ZIP download as publication.

## Visual system

Keep the canonical ContextQA logo and place it on a contrasting dark surface. Use a restrained neutral canvas, readable document typography, one brand action color and semantic statuses with icons/text. Proposed spacing scale: 4/8/12/16/24/32/48 px; controls at least 40 px high and touch targets 44 px where practical. Body 16 px, metadata at least 12 px, document reading measure roughly 65–80 characters. Dense tables may use 14 px, but not long-form guide content. Color never carries status alone. Target WCAG 2.2 AA; validate actual rendered contrast and keyboard flows.

Reusable primitives: app shell, workspace switcher, page header, source chip, status badge, empty/error state, stage timeline, table with selection, diff card, question round, media figure, save indicator, confirmation dialog and toast. Keep raw payloads under diagnostic details for operators, never the main user journey.

## Interaction quality checklist

- Show pending state immediately; disable duplicate submissions while the same operation is in flight.
- Every form supplies inline validation, server errors, clear saved/unsaved status and retry recovery.
- Preserve editor text across recoverable failures; use revision conflicts rather than last-write-wins.
- Explain blocked buttons with a specific prerequisite and link to fix it.
- Modal focus is trapped and restored; Escape closes only when doing so cannot lose work silently.
- Route changes/back button respect dirty edits; refresh restores durable run/review state.
- Empty onboarding differs from empty search and from failed data load.
- Use counts only with clear denominators: captured, selected, reviewed, published and replay-passed differ.
- A user can finish the core journey without reading CLI syntax, hashes or internal object IDs.

## Output design is part of product quality

The guide renderer needs contents navigation, title/summary, prerequisites, task-focused sections, useful screenshots near relevant steps, accessible captions/alt text, verification and troubleshooting. Use `learning.contextqa.com` as the requested editorial benchmark; the prior manual-browser sample demonstrates layout only, not compliant execution evidence. Assess one finished guide side by side before scaling batch generation. Keep prose and media usable on mobile and printable without clipped code or tiny images.
