# Salesforce context and verification learning pathway

Eight guided modules for admins, QA teams and implementation partners. Duration estimates are optional planning aids, not validated completion times. These are ContextQA starter exercises, not Salesforce certifications or substitutes for official product training.

| Module | Learn | Lab | Observable completion |
| --- | --- | --- | --- |
| 1. Org context | Configuration, intent and observed behavior differ | Complete the onboarding worksheet for one fictional journey | Every unknown is labeled; no credentials appear |
| 2. Discovery | What API describes can and cannot establish | Inspect the synthetic context and identify its visible fields | Learner distinguishes selected scope from full org coverage |
| 3. Sales Cloud | Positive/negative/boundary scenarios | Map Lead required fields; compare standard and custom quote mappings | One approved draft plus explicit unresolved mappings |
| 4. Service Cloud | Routing, closure and timed conditions | Write a case routing/closure matrix | Expected queue, role, timing and exception owner are named |
| 5. Personas and automation | Admin access is not user proof | Design one allow/deny check and one Flow negative path | Separate expected policy from actual configuration |
| 6. Integrations and release risk | Auth success is not a successful order | Prepare OAuth applicability and reconciliation questions | Both systems and timing/duplicate policy are covered |
| 7. ContextQA evidence | Plans, runs and selected result hierarchy | Inspect an approved result selection; do not execute without scope | Correct environment and case/step relationships identified |
| 8. Documentation maintenance | Guides need evidence and refresh review | Prepare a draft; compare separately reviewed example exports | Draft, approved guide and current proof are not conflated |

## First lab: no account required

Follow [the adaptation tutorial](../guides/adapt-assets.md). The synthetic fixture should prepare one reviewable candidate and 23 blocked candidates. Explain why “blocked by context” is useful information. Remove the confirmed rule and rerun into a fresh directory: zero scenarios should become reviewable. Change the environment to non-sandbox: write-based starter scenarios must remain blocked.

The result is a learning exercise, not a real Salesforce pass. Actual execution requires a separately authorized Salesforce environment, ContextQA tenant, identities, data and charge scope.

## Knowledge check

1. A field exists and an API describe succeeded. Is its intended business meaning proven? **No: owner intent is separate.**
2. An administrator can edit Amount. Does this prove a sales rep can? **No: test the intended identity and record scope.**
3. A run completed with skipped steps. Can it support a blanket success claim? **No: inspect scoped assertions and unresolved outcomes.**
4. A quote object has a similar label in two packages. Can we reuse totals unchanged? **No: confirm field semantics, currency and calculation timing.**
5. A new screenshot differs from an old one. Is the new process automatically correct? **No: compare to the approved rule and review the evidence.**
6. An API token is valid. Does it authorize billed workflow execution? **No: target, actions, data and potential charges must be authorized.**

## Capstone

Choose one journey. Deliver its context record, owner-approved rule, scenario mapping, environment/persona plan, evidence checklist and guide draft. In a live authorized capstone, add actual results and reviewed media. Another reviewer must be able to trace each assertion back to its rule and identify gaps without asking the author.

Recommended official learning topics: [Flow testing](https://trailhead.salesforce.com/content/learn/modules/flow-implementation-1/create-flow-tests) and [permission-based tests](https://trailhead.salesforce.com/content/learn/modules/unit-testing-on-the-lightning-platform/permission-based-tests). Check availability; no Salesforce affiliation is implied.
