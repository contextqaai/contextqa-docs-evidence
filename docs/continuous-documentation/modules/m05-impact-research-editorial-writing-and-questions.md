# M05 — Impact research, editorial writing and questions

Status: planned; phase: Pilot. Dependencies: M03,M06.

## User outcome

A request becomes a complete, useful guide or a justified no-change result, with no unsupported facts.

## Existing foundation

`agent.py; guides.py; writer.py; scripts/docs-agent-draft.js`

## Scope and workflow

Audience/goal/source brief; relevant article matching; outline before prose; style, protected terms and example-based templates; bounded writer calls; citations; structured question rounds; revision requests. Preserve user-authored prose and approved unaffected sections.

Follow the relevant screens and interaction states in [UX specification](../ux-spec.md). Every workflow includes empty, loading, permission-denied, failed and retry/recovery states; no stub screen qualifies as completion.

## Data and API contract

GuideBrief, Outline, Claim, SourceReference, TemplateVersion, QuestionRound; proposed drafting and writing-settings APIs. Pin prompt/model/config versions and record unknown usage explicitly.

All new contracts follow [architecture.md](../architecture.md). Enforce tenant/role access and optimistic revisions server-side; API names above are proposed until implemented.

## Implementation tickets

- **M05-T01:** Connect impact mapping to imported docs and source scope; expose reasons and unmatched areas.
- **M05-T02:** Create brief/outline and capture-plan handoff; choose tutorial/concept/reference template.
- **M05-T03:** Generate typed editorial spec from reviewed facts and ContextQA evidence; compile with existing guide engine.
- **M05-T04:** Persist question/answer rounds and validate content, references, media and unchanged sections.

Each ticket must carry the specific acceptance criteria it satisfies, implementation evidence and a recorded validation outcome in BACKLOG.csv.

## Acceptance criteria

- AC-1: A guide explains purpose, prerequisites, exact actions, expected result and supported recovery, rather than listing test steps.
- AC-2: Every procedural claim has evidence; unknown permission/limit becomes a question.
- AC-3: No-change source produces a reasoned no-op and no latest-version churn.
- AC-4: Partial answers save; only submitted round resumes once; later revision invalidates approval.
- AC-5: Reader can complete the benchmark task and reviewer scores it against acceptance.md.

## Failure and verification requirements

Validate domain/API behavior with deterministic fixtures and the relevant real PostgreSQL tests. Validate product journeys through saved ContextQA cases on the exact candidate build. Include at least one negative/permission case and one recovery case. A skipped or unavailable provider check stays pending; mocked adapter tests do not establish live integration. Capture the resulting UX at desktop and mobile sizes through the approved test workflow.

## Boundaries and risks

Proposed improvement: editable versioned tone, unlike reference read-only tone. No mandatory model vendor; preserve existing optional provider adapters.
