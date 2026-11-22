# Module build order

These are dependency gates, not calendar promises. Each module has concrete tickets and acceptance criteria. Do not build all modules at once.

## Release sequence

1. **Foundation:** M00 → M01. Establish real navigation, states, setup and access.
2. **Connected inputs:** M02 → M03 → M04. Real docs/source ingestion and durable runs.
3. **Useful output:** M06 → M05 → M07. ContextQA evidence, a complete guide and role-safe review.
4. **Complete first loop:** M08 → M09 → M10. Edit/conflict handling, image-bearing PR delivery, publication receipts and selective refresh.
5. **Pilot release gate:** M15. Its infrastructure requirements start during foundation; full restore/failure/deployment acceptance finishes here.
6. **Parity expansion:** M11, individual M12 providers, M13 reader/migrations and M14 media features according to pilot demand.
7. **Enablement expansion:** M16 after the source-to-guide refresh loop is reliable.

## First vertical-slice milestone

Use Kan or a controlled ContextQA fixture app with an identifiable deployed revision. One guide, one saved journey, one docs repository, one editor. Supply a goal, capture/replay, write a complete guide, review, create a PR including images, independently merge in the test repository, observe publication, then change one real UI label and repeat. Also run a no-change refresh and a failing capture. This milestone consumes narrow slices of M00–M10 rather than pretending every module is complete.

## Module index

| ID | Module | Phase | Dependencies |
|---|---|---|---|
| [M00](modules/m00-application-foundation-and-design-system.md) | Application foundation and design system | Pilot | none |
| [M01](modules/m01-workspace-onboarding-identity-and-roles.md) | Workspace onboarding, identity and roles | Pilot | M00 |
| [M02](modules/m02-github-connections-and-source-intake.md) | GitHub connections and source intake | Pilot | M01 |
| [M03](modules/m03-knowledge-base-import-and-content-inventory.md) | Knowledge-base import and content inventory | Pilot | M02 |
| [M04](modules/m04-durable-runs-and-workflow-automation.md) | Durable runs and workflow automation | Pilot | M02,M03 |
| [M05](modules/m05-impact-research-editorial-writing-and-questions.md) | Impact research, editorial writing and questions | Pilot | M03,M06 |
| [M06](modules/m06-contextqa-journey-discovery-execution-and-capture.md) | ContextQA journey discovery, execution and capture | Pilot | M01,M04 |
| [M07](modules/m07-review-inbox-collaboration-and-handoff.md) | Review inbox, collaboration and handoff | Pilot | M01,M05 |
| [M08](modules/m08-article-editor-change-sets-and-conflict-resolution.md) | Article editor, change sets and conflict resolution | Pilot | M03,M07 |
| [M09](modules/m09-reviewed-delivery-and-publication-receipts.md) | Reviewed delivery and publication receipts | Pilot | M02,M08 |
| [M10](modules/m10-continuous-refresh-health-and-dependency-graph.md) | Continuous refresh, health and dependency graph | Pilot | M04,M09 |
| [M11](modules/m11-ask-cli-and-assistant-mcp.md) | Ask, CLI and assistant MCP | Parity | M07,M09 |
| [M12](modules/m12-additional-source-and-help-center-integrations.md) | Additional source and help-center integrations | Parity | M02,M09 |
| [M13](modules/m13-hosted-docs-reader-migrations-and-api-reference.md) | Hosted docs reader, migrations and API reference | Parity | M03,M09 |
| [M14](modules/m14-media-editing-and-recording-assisted-intake.md) | Media editing and recording-assisted intake | Parity | M06,M08 |
| [M15](modules/m15-production-operations-and-release-readiness.md) | Production operations and release readiness | Pilot gate | M09,M10 |
| [M16](modules/m16-continuous-product-enablement-assets.md) | Continuous product enablement assets | Expansion | M10,M14 |

## Scope decisions

- Do not rebuild the evidence engine, replace FastAPI or introduce REA/browser automation alongside ContextQA.
- Keep docs in the existing repository/hosting platform before building M13.
- Implement one additional connector through the full lifecycle before adding the rest.
- Keep review mandatory for the pilot; scheduled research never implies scheduled publication.
- No time estimate from the attached payments-demo instructions applies here. Estimate tickets after baseline validation and dependency sizing.
- M00 implementation and local checks are complete. Deployed viewport acceptance is pending. M01 is next. See the [M00 implementation receipt](m00-implementation.md).
