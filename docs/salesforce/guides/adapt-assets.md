# Turn reusable scenarios into customer-specific review drafts

**Outcome:** prepare scenarios against a dated org context without inventing business expectations or running anything.

## Inputs

Use [catalog.json](../../../examples/salesforce/catalog.json) and a private context shaped like [the synthetic fixture](../../../examples/salesforce/context.synthetic.json). Supply schema version, org identity, capture time, environment classification, visible object fields, owner-confirmed rules, approved persona references and integration mappings. Business rules need status, value, owner, source and version. Keep credentials elsewhere.

For an existing org, collect actual configuration and ask owners to confirm intent. For a greenfield org, derive intent from approved process requirements; missing configuration is expected and remains a gap rather than a generated pass.

## Reuse an SX360 snapshot

Export a hydrated snapshot through the trusted SX360 snapshot-store API into private storage. Its raw on-disk snapshot uses blob references and is not sufficient by itself. Then:

```sh
python3 scripts/salesforce-context-from-sx360.py --snapshot /private/path/hydrated-snapshot.json --out /private/path/NEW-schema-context.json
```

This adapter copies only fresh object/field schema and source identity/time. It excludes Apex, XML and business-record data. It leaves business rules empty and sandbox identity unknown. Confirm the real org/environment and add approved rules/personas before preparing scenarios. It does not transform configuration into confirmed business intent.

## Prepare

```sh
python3 scripts/salesforce-prepare.py --context /private/path/org-context.json --out /private/path/NEW-preparation
```

Read `prepared-scenarios.json`. Every scenario is `needs_context` or `ready_for_review`, and every proof remains `not_checked`. Inspect its blockers, exact bindings and independent rule. The script performs no network operations and creates a new private output directory. Duplicate asset IDs, unsupported schema versions, known credential keys and reused output paths are rejected. A 14-day freshness window is a local preparation policy, not a Salesforce guarantee.

## Map custom objects explicitly

An org may use a packaged quote object rather than standard Quote. Add an owner-reviewed mapping, for example:

```json
{"mappings": {
  "Quote": {"target":"CustomQuote__c","status":"confirmed"},
  "Quote.GrandTotal": {"target":"CustomQuote__c.ApprovedTotal__c","status":"confirmed"}
}}
```

These are fictional names. Field existence is checked against supplied schema; business equivalence is not automatically established. Confirm currency, rounding, tax, line totals and timing before approving a total mapping. A suggested mapping cannot unlock readiness.

## Hand off to ContextQA

Select one scenario and resolve every blocker. Independently confirm actual tenant/workspace and environment; inspect available authoring tools or the [token adapter contract](../../contextqa-api.md). Author a reviewed case with real locators, data and assertions using that surface. This starter does not emit a directly importable ContextQA DTO or auto-create cases. Review saved configuration before authorizing a run. Preserve accepted run IDs and selected result hierarchy for the documentation workflow.

Completion means a reviewed custom scenario, not a passing test. Record execution, outcome, cleanup and guide review only after they actually happen.
