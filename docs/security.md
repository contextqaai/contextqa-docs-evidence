# Security and publication disposition

Real result records and browser traces can contain workspace/customer content, signed artifact URLs, DOM snapshots, console/network data, screenshots and recorded credentials. This is an actual sharing risk. Keep customer evidence outside GitHub and partner uploads unless separately reviewed and authorized.

The repository contains wrapper source, documentation, tests and synthetic examples only. Workspaces, credentials, raw captures, signed URLs and recordings are excluded. A private repository limits visibility but does not make raw evidence safe to upload. No existing product repositories, backend code or tokens are copied here.

## Current controls

- Local result reads use a fixed origin, explicit endpoint allowlist, no redirects, bounded response sizes and verified result-parent bindings. No paid execution calls or remote media downloads.
- Trace import rejects traversal/symlink paths and excessive expansion; it selects generic actions and screenshot resources, not DOM/network bodies.
- Shareable output is rebuilt from reviewed text and attached allowlisted media. Unattached frames and private inputs remain local.
- Content and media hashes bind review to the export; edits invalidate approval. Comparison requires intact reviewed exports and explicit complete step mapping.
- Static HTML escapes text and restricts scripts/network/frames. A sandboxed iframe snippet points only at the chosen future static host. Nothing is deployed automatically.

## Limits that require human review

Text filtering cannot reliably detect every secret or personal detail. Images, audio/video and embedded metadata are not automatically redacted or stripped. Media headers are checked but files are not fully decoded or malware scanned. The private trace still contains sensitive source data and needs an appropriate retention policy.

Approval receipts are local workflow safeguards, not signatures or a tamper-proof security boundary. A person with local write access can forge them. Parent-directory symlinks, concurrent file replacement and hostile multi-user environments are outside this prototype's trust model. Do not run it as a web service for untrusted tenants.

Comparison detects changed text/media identity, not semantic UI differences, correctness, permissions or pixel-level regressions. Release explanations are user-provided and must be verified. Review media and change drafts before sharing; approve destination documentation changes separately.

## Publication gate

Do not publish raw traces, HARs, recording workspaces, `.env` files, credential exports or real API responses. Share wrapper source and synthetic examples only. A production service needs a dedicated security review, tenant isolation, scoped secrets, quotas, authenticated artifact access, retention/deletion, redaction tooling and auditable approvals before general availability.
