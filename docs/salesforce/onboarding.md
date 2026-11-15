# Onboard a Salesforce org with useful business context

Start with one environment and three critical journeys. Use the [onboarding CSV](../../examples/salesforce/onboarding.csv) as a spreadsheet; keep each answer's owner, source and review date. Unknown is an acceptable answer and becomes an explicit decision request.

## First conversation

Ask: what must launch, by when, who signs off, and what would a failure disrupt? Identify a business owner, Salesforce admin, verification lead and integration owner. Agree which org/environment is in scope. A Developer Edition org is not automatically a sandbox; record its actual classification.

## Access and collection

Arrange an authorized OAuth connection separately from the questionnaire. Do not put credentials or tokens in files intended for Git or a content provider. Establish the API identity's permitted metadata and record scope. REST describes supply object/field relationships; Tooling API access varies by object and permission. Metadata retrieval is separate from listing names. An access error is unknown coverage, not proof a feature is absent.

Collect only the allowed schema first. Document package names, custom objects, automation, role mappings and integration references privately. Record org ID, environment, API version, capture time, collector version and failed/skipped categories. A schema visible to one identity does not establish effective access for every persona.

## Owner interview

For each journey, document trigger → steps → expected outcome → exceptions. Ask for thresholds with exact equality behavior, currencies, timing, approval roles, record ownership and downstream effects. Keep what the SOP says separate from what configuration currently enforces. Ask owners to resolve discrepancies; do not silently copy implementation into expected results.

## Execution charter

Before write-based tests, approve objects/actions, isolated users, seed data, outbound emails/callouts, integrations, run volume, potential charges, cleanup and stop conditions. Confirm the selected ContextQA tenant/workspace, environment and plan. A login or API credential does not approve a billed run. Keep result and media sharing decisions separate from test execution.

## Deliverable and acceptance

Return a context pack with confirmed rules, unknowns, source links, candidate mappings and prioritized scenarios. A customer should be able to identify their process owner, see an actual source for each implemented fact, understand why each selected scenario applies, and see what is still unverified. Start with one fully traceable journey before expanding.

Sources: [Salesforce object describe](https://developer.salesforce.com/docs/platform/api-rest/guide/resources-sobject-describe.html), [Tooling API resource permissions](https://developer.salesforce.com/docs/platform/api-tooling/guide/intro-rest-resources.html), [ContextQA adapter boundary](../contextqa-api.md).
