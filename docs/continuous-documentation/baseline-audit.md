# Existing implementation: reuse and gaps

Pull request #10 merged the inspected implementation (`c2a9572`) into `main` at `1d62a9a1fe5fcdcdc6ca573e782bdaad07f523df`. Git reports identical file trees for these commits. This audit therefore applies to the merged baseline. The local implementation branch `feat/continuous-documentation-platform` starts at that merge.

At inspection, `.github/workflows/test.yml` was modified and `examples/learning-quality/` was untracked. Preserve both. Planning changes add this directory and pointers in existing documentation only. Do not merge or overwrite the other work as part of plan consumption.

Earlier chat located: “https://docs.pageloop.ai/guides/how-pageloop-works reverse…” (`01a1f252-8eae-7f22-a3e5-e0056d81893a`). Its latest work includes ContextQA-only writing and OrangeHRM URL-bootstrap examples. The older CLAUDE-HANDOFF predates those changes; its known build failure is superseded by later validation receipts.

| Component | Inspected evidence | Reuse decision | Remaining product work |
|---|---|---|---|
| React console | `apps/web/src/App.tsx`, `pages.tsx`, `Review.tsx` | Keep React/TypeScript and existing components | Current areas are inbox, articles, sources, health, activity and settings. No complete onboarding, workflow builder, connected capture setup or hosted reader product. |
| Review domain | `cqa_artifacts/loop.py` | Preserve decisions, optimistic versions, approval hashes and evidence gates | Existing decisions are primarily article-level. Add structural changes and finer-grained review without weakening approvals. |
| Hosted API/auth | `cqa_artifacts/hosted/server.py`, `auth.py` | Extend FastAPI and OIDC abstraction | Existing mutations cover events/articles/review/approve/bundle/apply-local. Membership management is operator provisioning, not a complete user-facing invitation flow. |
| Storage | `hosted/store.py`, `migrations/001_hosted.sql` | Keep PostgreSQL | Project state is a JSONB aggregate locked per project. Add explicit jobs, connections, artifacts and receipts; move growing collections incrementally rather than rewriting every domain object first. |
| Repo agent | `agent.py`, `.github/actions/docs-agent/action.yml` | Reuse plan/validate/submit/prepare | Turn operator steps into discoverable setup and durable hosted runs. CI template presence is not evidence of an executed hosted pipeline. |
| Intake | `loop_sources.py` | Reuse GitHub signature normalization and transcript segmentation | Add hosted webhook lifecycle, scope selection, delivery receipts, deduplication and reconnect UX. |
| ContextQA journeys | `journeys.py`, `examples/orangehrm/` | Reuse saved-case registration, maintenance and evidence binding | Productize URL + goal bootstrap; independently replay generated journeys; show partial coverage and unsupported cases. |
| Editorial compiler | `guides.py`, `docs/editorial-guides.md` | Reuse typed guide sections, figures and source mapping | Agent still supplies editorial and visual judgment. Add persistent brief/outline/review UI and quality evaluation. |
| Evidence writer/library | `writer.py`, `library.py`, `frames.py` | Reuse collect/finalize, immutable versions and frame checks | Integrate into hosted jobs/storage/UI; do not treat file-local output as published documentation. |
| Delivery | `loop_git.py` | Reuse intent journal and target/baseline checks | Text-only draft PR adapter; complete image/navigation packaging, status reconciliation and live publication verification. |
| Health | `pages.tsx` HealthReport | Reuse missing coverage/age/relative-link checks | Age is not semantic correctness. Add dependency-driven refresh and accurate scope labels. |

## Evidence we already have, with boundaries

- `docs/hosted-validation-2026-11-19.md`: historical React build/tests and PostgreSQL checks; no real OIDC, Docker, production or remote CI acceptance.
- `docs/journey-validation-2026-11-20.md`: historical local checks and drift/collection findings.
- `docs/contextqa-writer-acceptance.md`: Kan case 186 passed 18/18 steps in results 445 and 447. The A/B difference was example data at the same revision, not a released product change. Four images came from an 800×450 ContextQA recording. Deployment was user-attested.
- `examples/orangehrm/coverage.md`: authentication replay passed 19/19 steps. Five other workflows had bootstrap results without independent saved-case replay. Leave submission was not covered. Original failed plan remains failed despite a later separate recruitment pass.

Do not reuse historical counts as new test results. The technical foundation is real, but repeated guide quality, autonomous orchestration, visual UX completion and production operation remain distinct gates.

## Easiest path

Keep one repository, one API, one database and one React console. Start with GitHub + ContextQA + Markdown/MDX. Use the existing docs hosting platform for the first release. Add the standalone reader/hosting product later. Keep CLI operation supported so the factory and CI can use the exact same services as the UI. Avoid a second browser stack, new general-purpose agent framework, billing system or all-provider integration sprint before the first publish-and-refresh journey passes.
