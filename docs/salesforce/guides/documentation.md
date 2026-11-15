# Create Salesforce guides from selected execution evidence

**Audience:** Salesforce admins, QA leads and implementation partners. **Starter assets:** SF-DOCS-01 and SF-DOCS-02.

## What you will cover

Reviewed instructions, screenshots and maintenance after change.

## Before you start

Choose the exact authorized ContextQA tenant/workspace, saved workflow, environment and selected completed results. Confirm sharing rights and inspect screenshots, video and logs separately for sensitive content.

## Walkthrough

1. Run only after the plan/data/environment and potential charge are approved. Preserve the accepted run ID once; an ambiguous timeout is not permission to restart.
2. Use the existing contextqa-collect command with actual run/case/step result IDs. Validate hierarchy and preserve raw private provenance.
3. Read every imported instruction. Attach only media that was actually retrieved and reviewed, using the existing fetch-media/attach flow where supported.
4. Approve and export only the reviewed guide. Use accurate outcome labels: a completed run can still have failed, skipped or inconclusive steps.
5. After a change, obtain new authorized evidence, create a separate reviewed export and compare explicit step mappings. Review the refresh draft before publishing.

## Evidence and acceptance

Expected output: an accurate scoped guide with evidence links and review history. The preparation tool produces a draft; it deliberately does not approve or publish it.

## Common failure to avoid

Automatic recapture, semantic visual diff, hosting and native partner publishing are not implemented by this repository. Missing video is not permission to fabricate a demo.

## Continue

[Map the reusable assets](adapt-assets.md) · [Learning pathway](../learning/pathway.md) · [Source register](../research/sources.md)

[Actual collection, review and export commands](../../contextqa-api.md) · [Existing documentation workflow](../../how-to-use.md).
