# Permissions: prove behavior for the intended personas

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-ACCESS-01 through SF-ACCESS-03.

## What you will cover

Record access, field visibility/editing and approval segregation.

## Before you start

Ask for approved test-user references and a role policy. Profiles and permission sets are inputs, not a complete effective-access verdict; record sharing, ownership and runtime context also matter. Do not export employee identities into public fixtures.

## Walkthrough

1. Write an expected-access matrix with object/action/field/record scope and persona. The business/security owner confirms it before execution.
2. Choose isolated records owned by the permitted and restricted personas. Confirm no administrative override masks the intended restriction.
3. Verify read and edit behavior through the relevant UI/API surfaces with each actual identity. Record which identity executed each assertion.
4. Attempt prohibited actions as negative tests, including self-approval where separation is required. A hidden UI button alone does not prove backend enforcement.
5. Review exceptions and cleanup. Attach result evidence to the approved matrix version.

## Evidence and acceptance

Expected output: allow/deny evidence per persona and scope. Missing user access is a blocker, not permission to substitute an administrator.

## Common failure to avoid

Do not describe a configuration scan as a completed segregation-of-duties or compliance assessment.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)
