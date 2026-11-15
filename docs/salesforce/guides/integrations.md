# Integrations: verify authentication and the business handoff

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-API-01 through SF-API-04.

## What you will cover

OAuth readiness, field/total reconciliation, duplicate messages and recovery.

## Before you start

Inventory each integration identity, source/target environment, middleware owner, authentication flow, mappings, currency, timing, retries and duplicate policy. Capture only safe configuration details; redact secret values while retaining nonsecret grant type and endpoint purpose.

## Walkthrough

1. Identify the integration method and approved authentication flow. Check official retirement guidance and actual applicability rather than assuming every integration is affected.
2. Verify token acquisition and a bounded permitted read in the intended org. Login success does not establish correct business processing.
3. With separate execution authorization, send one synthetic transaction and compare its source/target correlation ID, total, currency and item count.
4. Exercise duplicate delivery and outage/recovery only in the agreed isolated environment. Check for missing and duplicate transactions after recovery.
5. Retain sanitized assertions and cleanup evidence. Treat inaccessible downstream systems as an explicit verification gap.

## Evidence and acceptance

Expected output: authentication evidence plus business reconciliation. Salesforce’s published username-password retirement date is February 20, 2027; recheck the official notice before each customer assessment.

## Common failure to avoid

Never skip request-body inspection simply because it may contain credentials. Use a supported redacted export that preserves authentication semantics. Do not expose or copy secret values.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)

[Salesforce retirement notice, checked November 14, 2026](https://help.salesforce.com/s/articleView?id=005461279&language=en_US&type=1).
