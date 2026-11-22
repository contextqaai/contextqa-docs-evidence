# M01 — Workspace onboarding, identity and roles

Status: implemented locally, in acceptance review. See the [M01/M02 results](../m01-m02-results.md) and [operator workflow](../m01-m02-operations.md). Pilot phase. Dependencies: M00.

## User outcome

An administrator can configure a workspace and invite a reviewer without an operator editing the database.

## Existing foundation

`hosted/auth.py; hosted/manage.py; docs_memberships`

## Scope and workflow

Resumable setup, real identity-provider sign-in, members/invitations, role limits, account settings and workspace selection. Setup progress derives from completed configuration, not manually ticked boxes.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

Membership, Invitation, SetupProgress; proposed workspace and membership endpoints with server-side role checks. Use existing OIDC identity integration; do not add a separate password store merely to mimic the reference.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M01-T01:** Complete real OIDC callback/session/expiry/relogin acceptance.
- **M01-T02:** Create workspace and resumable setup checklist.
- **M01-T03:** Implement invitations, expiry/resend and member role/deactivation operations.
- **M01-T04:** Enforce role and assignment policy on every route, search, artifact and export.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: Interrupted setup resumes with saved branch/root and no duplicated workspace.
- AC-2: Editor cannot invite Admin; users cannot remove/demote the last active Admin.
- AC-3: Contributor receives 404/denial for unassigned item IDs and never finds them in search.
- AC-4: Membership revocation blocks new API/artifact requests even in an already-open browser.
- AC-5: Expired invitation and expired session each have distinct recovery paths.

## ContextQA journey and reader guide

**Resume workspace setup and invite a teammate.** As an admin, save a partially configured workspace, sign back in, resume at the saved step, then invite a teammate. Capture the resumed checklist and confirmed membership after the teammate accepts a test invitation.

**Negative and recovery coverage.** As an editor, try to grant Admin. Verify denial and unchanged membership after reload. Distinguish the recovery instructions for an expired invitation from an expired session.

Apply the [feature verification and guide workflow](../feature-verification.md) to each shipped feature. Map additional cases to the remaining criteria in this module. Record the visual review, assertion results and guide disposition in the ticket receipt.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Deferred: enterprise directory sync. Reference account password behavior is not copied when authentication is delegated to OIDC.
