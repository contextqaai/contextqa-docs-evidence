# Sales Cloud: test the journey, not just the save button

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-SALES-01 through SF-SALES-06.

## What you will cover

Lead intake, duplicate handling, conversion, opportunity progression, quote approval and ownership transfer.

## Before you start

Confirm whether the customer uses standard quotes, a managed CPQ package or another revenue product. Collect mandatory fields, duplicate policy, conversion mappings, allowed stages and approval thresholds. Object names alone cannot identify the commercial process.

## Walkthrough

1. Prepare one isolated lead with the approved matching and ownership attributes. Test required-field and duplicate behavior independently before conversion.
2. Convert through the approved path and check resulting account/contact/opportunity relationships using bounded record assertions.
3. Exercise the mapped opportunity stage gate with both satisfied and missing prerequisites. Capture the rejection as well as the successful transition.
4. For discount approval, test below, exactly at and above the owner-approved threshold. Confirm who may approve and whether sending the quote is blocked.
5. Check downstream effects and cleanup. A successful UI notification is insufficient if the resulting record links or integration totals are wrong.

## Evidence and acceptance

Expected output: a rule-linked matrix covering positive, negative, boundary and persona variants. Avoid using arbitrary percentages or stage labels from this guide as customer requirements.

## Common failure to avoid

An admin-only pass, a standard Quote template mapped blindly to a packaged quote, or ignored duplicate warnings can conceal a real failure.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)
