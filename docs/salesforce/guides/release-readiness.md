# Release readiness: separate applicability, impact and proof

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-RELEASE-01 and SF-RELEASE-02.

## What you will cover

Seasonal release updates, configuration drift and release evidence.

## Before you start

Record intended org, candidate environment, advisory version, source-check date, current release scope and baseline/candidate snapshots. Confirm preview or target-version relevance rather than assuming any developer org proves customer readiness.

## Walkthrough

1. Review official release notices and mark each scoped item applicable, not applicable with evidence, or unknown.
2. Map applicable items to org components and business rules. For a custom change, compare the intended baseline and candidate snapshots.
3. Disclose incomplete discovery and unresolved dependencies. A newly expanded scan is not necessarily a new deployment.
4. Select affected scenarios with the owner. Verify their environment, rule version, personas and test-data contract before running.
5. Review current step-level evidence, failures, blocked checks, coverage gaps, exceptions and rollback ownership. Keep the readiness decision separate from deployment approval.

## Evidence and acceptance

Expected output: an evidence-backed readiness pack with unresolved items visible. A green dashboard without scoped proof is not a release decision.

## Common failure to avoid

Old successful runs, mismatched sandbox names, zero-step passes and unreviewed advisories must not become current release evidence.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)
