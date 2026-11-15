# Flow and Apex: combine local checks with business verification

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-FLOW-01, SF-FLOW-02 and SF-APEX-01.

## What you will cover

Automation entry conditions, negative paths, fault behavior and bulk operations.

## Before you start

Inventory identifies that automation exists; full definitions and accessible source are required to understand its branches. Gather the approved behavior independently, including affected objects, user/system context and external effects.

## Walkthrough

1. Identify the active version and entry conditions. Map relevant configuration/source evidence to a named business rule.
2. Build positive and negative examples. Include null values, equality boundaries and record states that should not enter the automation.
3. Plan fault-path coverage and bulk cases under an isolated data/side-effect charter. A retry can duplicate downstream work unless the expected contract prevents it.
4. Inspect unit-test outcomes and selected business-process assertions separately. Code coverage or a single unit-test pass does not prove the end-to-end journey.
5. After a change, rerun affected approved scenarios and compare observed outcomes to the current rule version.

## Evidence and acceptance

Expected output: branch-to-rule coverage, actual execution evidence and a record of untested paths. This starter does not parse all Flow/Apex semantics or execute unit tests.

## Common failure to avoid

Dynamic dependencies, protected package internals and excluded metadata must remain coverage limitations rather than assumed-safe components.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)

[Official Tooling API resources](https://developer.salesforce.com/docs/platform/api-tooling/guide/intro-rest-resources.html) document distinct read and execution operations; this guide does not authorize execution.
