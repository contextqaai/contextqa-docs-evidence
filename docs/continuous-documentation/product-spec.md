# Product requirements

## Outcome and users

Build a continuous documentation platform that converts product change evidence into accurate, illustrated, reviewable documentation and keeps it synchronized after releases. Primary users: technical writers, documentation owners and solutions engineers. Developers supply change context and receive actionable docs checks. Subject experts review assigned work. Administrators configure sources and access. Readers consume approved documentation, not execution logs.

Success is measured by accepted useful guides and reliable updates, not number of generated pages. Pilot metrics: setup completion, time to first reviewed guide, fraction of drafts accepted with small edits, reviewer minutes per guide, unsupported claims found in review, refresh latency after a verified release, no-change churn, capture success and cost per accepted update. Record baseline values before claiming improvement.

## First-release scope

One workspace can connect product and docs GitHub repositories, import docs, bind a ContextQA workspace/environment, create a guide request, generate or reuse a saved journey, collect actual evidence, review text/images/questions, deliver a Markdown/MDX PR, and track whether it merged and reached the configured destination. Scheduled and merged-PR workflows create review work without silently publishing it.

Later parity: additional source/help-center integrations, visual KB editing, reader hosting with domains and versions, richer media, assistant MCP and chat, API-reference migration. Later expansion: training and sales assets. See module-specific scope in roadmap.md; listing a feature is not a commitment to ship every module in the pilot.

## Role contract (proposed)

| Action | Admin | Editor | Contributor |
|---|---|---|---|
| Read knowledge base | Yes | Yes | Yes, within workspace access |
| View/review proposals | All | All | Assigned only, enforced in API/search/export |
| Edit assigned proposal and answer questions | Yes | Yes | Yes |
| Assign, archive or resolve | All | All | Archive/resolve own assigned work only |
| Start documentation runs/manage workflows | Yes | Yes | No |
| Approve and deliver documentation | Yes | Yes | No; handoff to publisher |
| Manage connections, secrets, capture policy | Yes | No | No |
| Manage style/templates | Yes | Yes | No |
| Invite | Any role | Editor/Contributor | No |
| Change member role | Other members; preserve last admin | No | No |

Readers and automation service identities are separate from these authoring roles. Contributor reassignment must revoke access immediately. Proposed enhancement: admins can deactivate members with an audit record; Pageloop's inspected Members page has no removal action. Keep product-specific role policies explicit rather than copying incidental limitations.

## Primary journeys

### J01: first usable guide

Admin signs in → creates workspace → connects docs repository → imports selected branch/root → binds ContextQA environment and credential reference → supplies product URL, audience, goal and allowed actions → sees coverage plan → starts authorized capture → reviews a complete guide in Inbox → answers missing facts → editor approves exact revision → creates docs PR → merge/build status reconciles → reader-facing guide verified. At each stage, refresh/navigation must preserve progress. A failed capture leaves a recoverable request, not an empty success page.

### J02: shipped change to refreshed documentation

Verified source event → deduplicate → identify reader-visible change and release/environment mapping → find dependent pages, claims and figures → reuse/maintain relevant saved journeys → run on the deployed version → draft only supported changes → compare old/new article and images → review/approve → deliver → observe publication. A merged product PR alone does not prove the running product contains the change. A no-op records its reasoning and leaves approved text unchanged.

### J03: contributor handoff

Editor assigns item → contributor sees only that item → reviews sources, edits wording and answers questions → selects ready-for-publish recipient and note → assignment changes atomically → previous contributor loses access → editor receives the same saved revision and completes review. Notification failure must not roll back or duplicate the handoff.

### J04: repair a failed or ambiguous run

Open run → identify failure stage (source/auth/deployment/journey/evidence/writer/delivery) → inspect sanitized explanation and linked receipt → repair inputs → retry only the safe stage. If ContextQA start may have been accepted, reconcile the upstream run rather than starting another. Preserve original failed attempts and distinguish bootstrap from replay.

### J05: direct docs edit with upstream conflict

Open article → create/select change set → edit content/metadata/navigation → save → upstream revision changes → compare base/ours/theirs → resolve per conflict → revalidate → invalidate old approval → preview → deliver. Never silently replace a teammate's edit; a clean textual merge still requires content review.

### J06: approved knowledge to enablement (later)

New approved guide version → determine affected release note, training lesson, demo and sales asset → draft audience-specific updates using approved claims and compatible captures → asset owner reviews → publish through a configured destination → show dependency revision and freshness. Do not convert raw failing tests into customer-facing launch claims.

## Data quality and content rules

Every procedural claim links to a source or ContextQA checkpoint. Observed behavior, reference facts and customer assertions remain distinguishable. Every published image has capture origin, selected checkpoint/frame, transformation lineage, alt text and reviewer. Credentials and signed URLs never become content. Guides explain goal, prerequisites, choices, steps, expected results and supported recovery; do not mechanically convert every test action into prose. Failed/stale evidence cannot replace the latest approved guide. Human approval binds content, media, source revisions and destination, and is invalidated when those change.
