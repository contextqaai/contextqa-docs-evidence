# PageLoop workflow parity matrix

**New research and forward plan (2026-11-21):** [45-page reference inventory](continuous-documentation/feature-inventory.md), [current code audit](continuous-documentation/baseline-audit.md), and [module plan](continuous-documentation/roadmap.md). The dated implementation matrix below remains historical; the new plan does not upgrade any verification claim.

Status date: 2026-11-19. This matrix compares publicly described PageLoop behavior with this independent, open-source implementation. It is not based on PageLoop code and does not use PageLoop branding. The PageLoop column restates `docs/pageloop-research.md` (official docs, product article and video transcript checked 2026-11-19). The official docs could not be fetched again from the 2026-11-19 implementation session because of a network allowlist, so re-check those pages before publishing a comparison.

**Status key.** *Implemented*: code exists and an automated test exercises it in this repository. *Partial*: some of the behavior exists; the gap is named. *Not implemented*: no code. "Evidence required" names the receipt that a release claim needs and that does not exist yet.

| Area | PageLoop behavior (public) | Status here | What exists | Gap / evidence required |
|---|---|---|---|---|
| Source configuration | Connect sources (repositories, help center, recordings) | Partial | Project manifest: repository, application URL, environment, instructions, sections with code paths, modules and keywords (`cqa_artifacts/loop.py`) | No UI to edit the manifest; no managed connector credentials |
| Merged-PR workflow | Run on merged PRs | Partial | `cqa_artifacts.agent plan/validate/submit`; composite action `.github/actions/docs-agent`; HMAC-verified GitHub merged-event normalizer (`loop_sources.py`) | Hosted webhook receiver not implemented; no remote CI run receipt |
| Scheduled workflow, pause, test run | Schedule, pause and test workflows | Not implemented | — | Needs durable job table, scheduler and pause state (backlog item) |
| Impact mapping | Find affected articles | Implemented | Code-path, module and keyword mapping; unmatched changes become questions (`ingest`) | Keyword matches are labeled for relevance review |
| Drafting | AI drafts article updates | Partial | Bounded plan; optional BYOK call `scripts/docs-agent-draft.js`; local coding assistant can write the proposal; `validate` enforces paths, baselines and the same limits as ingestion | No paid drafting receipt; no hosted drafting worker |
| Inbox review | Inbox of updates with status | Implemented | React inbox with search, filters, metrics; PostgreSQL state | React acceptance on a real identity provider not done |
| Per-change decisions | Accept / ignore / undo | Implemented | Accept, dismiss, undo per article; optimistic versions | — |
| Markdown editing | Edit suggested article | Implemented | Editor with unsaved-change protection; React test saves exact text against the current version | — |
| Reasons, sources, questions | Show why, link sources, agent asks questions | Implemented | Context panel with source link, reason, ContextQA verification, questions as a review gate | — |
| Roles and handoff | Contributors, editors, assignment | Implemented | Admin/editor/contributor memberships in PostgreSQL; assignment; contributors cannot approve | OIDC tested with generated JWTs only |
| Change sets | Group changes, deliver together | Implemented | One request = one change set; hash-bound editor approval invalidated by any later change | — |
| Drift checks | Detect outdated docs | Partial | Content health: missing coverage, stale baselines, broken relative links, now shown as actionable groups | No semantic drift check; no external link crawl |
| Screenshots | Automated capture from app workflows | Partial | Reviewed ContextQA exports attach as evidence; failed or missing capture blocks delivery | No fresh run for Kan PR #15; media mapping into draft PRs not implemented |
| Video to docs | Segment recording into doc updates | Partial | Transcript-segment intake with bounds | No transcription, frame selection or recorder |
| Publication | Explicit publish / draft PR | Partial | Reviewed ZIP; explicit text-only draft-PR adapter with intent journal, never merges | No remote draft-PR receipt; evidence-bearing bundles need ZIP delivery |
| Developer integration | Fits developer workflow | Partial | CLI, composite action, workflow template, React review console on the same PostgreSQL change set | End-to-end CI → hosted submit not executed against a deployed instance |
| Deployment | Hosted SaaS | Partial | Dockerfile, compose, migrations, health check; CI jobs for web and hosted suites proposed in `outputs/proposed-ci/test.yml` (not yet applied) | Docker image build not executed (registry blocked in the validation environment); no production deployment, backup or retention policy |

## Release gates still open

1. A Docker image build and compose run receipt.
2. OIDC acceptance with a real identity provider (discovery, CSP connect-src, expiry, relogin, callback).
3. Durable job queue, scheduler and webhook receiver for automatic intake.
4. A fresh, authorized ContextQA run for Kan PR #15 at an attested deployed revision, after the `PRE_Login` URL assertion is corrected.
5. A remote CI run of `.github/workflows/test.yml` and of the docs-agent action.
