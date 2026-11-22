# Phase 11 — Application security

Run a risk review for each release and repeat affected checks when code, dependencies, permissions or deployment settings change. Link Phase 6 identity and tenant-isolation receipts to A01 and A07. For each category record the control, owner, candidate SHA, environment, expected and actual outcome, evidence, and disposition. Use ContextQA browser and API assertions for normal access, denials and recovery with designated test identities. Use dependency inventory, configuration review, code review and operator alert receipts for controls the runner cannot observe.


A01 Broken Access Control — verify reader, editor and administrator permissions and synthetic tenant isolation.

A02 Security Misconfiguration — verify production authentication mode, allowed origins and the publishing repository and branch.

A03 Software Supply Chain Failures — review pinned dependencies, lockfile changes, build provenance and outstanding dependency advisories.

A04 Cryptographic Failures — verify encrypted transport, the secret binding and redacted logs. Confirm credential rotation with the owner.

A05 Injection — verify that user-authored markup renders as text and database operations bind user input as parameters.

A06 Insecure Design — verify that private content is held before disclosure and that public approval covers the exact guide and media.

A07 Authentication Failures — check anonymous, expired and revoked fixture identities and the authorized recovery journey.

A08 Software or Data Integrity Failures — check approved media digests and verify that a stale version or changed target requires a new review.

A09 Security Logging and Alerting Failures — correlate an allowed and denied fixture action to redacted audit records. Confirm the test alert reaches its intended owner.

A10 Mishandling of Exceptional Conditions — simulate provider unavailability in the adapter harness and verify that retry preserves one logical draft PR.

Classify each category as passed for the listed controls, failed, blocked, or inapplicable with an owner and rationale. Hold release for unresolved critical or high findings and required controls without evidence. Preserve findings, remediation and rerun receipts. The review covers the named controls on the recorded build.

[OWASP Top 10:2025 risk categories](https://owasp.org/Top10/2025/)

## Publishing module evidence

| Risk | Evidence for the publishing change | Open release evidence |
|---|---|---|
| A01, A07 | Hosted route tests denied an editor. Authentication regressions checked signature, audience, expiry, scope and tenant isolation. | Repeat with the staging identity provider. |
| A02 | A mismatched destination stopped before requesting a GitHub credential. Hosted configuration tests also rejected production development-auth mode. | Verify the real App installation lists only the approved repository. |
| A03 | The pinned Mistune 3.4.0 wheel matched the registry SHA-256 `d03cec4c8620f21517a996d82d14f3b59c30d79bda2cc6c56bd32b839f18ce6b`. The version metadata listed no active advisories on 22 Nov 2026. [PyPI release](https://pypi.org/project/mistune/3.4.0/) | Review the full transitive inventory and record build provenance for the release. |
| A04 | The adapter requests a short-lived installation token over HTTPS. | Confirm the deployment's key storage and rotation with its owner. |
| A05 | The renderer test checked escaped literal markup and rejected an unreviewed link. | Review newly introduced input or output formats when they change. |
| A06 | The disclosure tests blocked a seeded credential, an internal-only note and private comments. A public decision was required for the preview. | A reviewer must inspect the pixels, audio and unmarked business statements in each guide. |
| A08 | Changed media bytes and an obsolete preview were rejected. The successful path copied the original bytes. | Verify the draft created by the scoped GitHub App. |
| A09 | The successful handoff records the actor, guide path, PR and preview digest in the project audit history. | Exercise the deployment's denied-access logging and confirm delivery of a test alert. |
| A10 | A simulated lost response after branch creation recovered the same branch and produced one PR. | Reconcile the live PR and Pages receipt after installation. |

The hosted publisher cases use disposable PostgreSQL and a simulated GitHub transport. The anonymous Pages reader has separate live evidence. [Publisher regression cases](../../tests-hosted/test_pages_handoff.py)

A repository maintainer can install the supplied workflow as `.github/workflows/publishing-security.yml`. Once installed, **Publishing security controls** runs the handoff and hosted identity suites with a disposable PostgreSQL service. GitHub retains the individual test outcomes in the check log. Deployment-only controls stay open until their owner supplies evidence. [Installable workflow](../../integrations/github/publishing-security.yml)
