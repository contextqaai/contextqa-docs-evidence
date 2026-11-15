# Service Cloud: verify intake, resolution and exceptions

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-SERVICE-01 through SF-SERVICE-04.

## What you will cover

Case routing, escalation, closure requirements and reopening.

## Before you start

Collect intake channels, queues, routing policy, priority definitions, business hours, holidays, entitlement assumptions, resolution requirements and notification destinations. Keep real customer messages and recipients out of fixtures.

## Walkthrough

1. Create a routing matrix with channel, priority, queue and owner. Ask the service owner to confirm each expected destination.
2. Use isolated synthetic cases for matching and nonmatching conditions. Inspect saved owner/status rather than relying only on screen text.
3. Define how time-dependent escalation will be tested: approved clock control or a bounded observation window. Do not rewrite service targets to make a test fast.
4. Attempt closure without and with the approved resolution information. Reopen and verify ownership, status and any applicable clocks.
5. Inspect email/callout effects only within the authorized charter; reconcile generated artifacts and cleanup.

## Evidence and acceptance

Expected output: case-state and routing evidence with actor, environment, rule version and observation time.

## Common failure to avoid

An inactive escalation, missing entitlement configuration or an unobserved timer is not a passing SLA test. Keep blocked checks explicitly unresolved.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)
