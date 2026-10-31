# Layerpath — optional tour handoff example

**Status: proposed, not executed.** No native project, exported tour or connector is
claimed. Historical sign-in readiness is not current feature-access evidence.

Start with the [Layerpath integration brief](../../docs/layerpath-integration.md) for
setup, a baseline-to-refresh walkthrough, responsibility boundaries and the interface
decisions to confirm with the Layerpath team.

## Why this example exists

This was originally a proposed “Layerpath documenting Layerpath” demonstration:
capture its authoring UI and create a sample tour of that same workflow. It was a
native-platform experiment, not a dependency of the documentation engine and not a
completed integration. The original target is retained in execution-status.json for
historical clarity.

The current primary path is **customer application → ContextQA tests and execution →
reviewed evidence → client-guided documentation → scoped refresh after changes**.
See the [usage guide](../../docs/how-to-use.md) and
[trigger design](../../docs/documentation-triggers.md). Kan is the recorded core
execution example; that evidence does not establish Layerpath acceptance.

## Optional role in the current design

A client may choose a tour-authoring destination after ContextQA has produced and the
owner has reviewed the evidence. Layerpath is one candidate for that handoff. Confirm
current account features, supported media intake, export formats and access before
using it; this repository does not implement or promise a Layerpath API adapter.

1. Capture the client's selected task using ContextQA, with isolated data and a known
   application revision where available.
2. Review selected screenshots/recordings and prepare the ordered instructions under
   the approved client documentation profile. Keep credentials and raw traces private.
3. If the destination supports the required intake, create a private sample using the
   reviewed assets. Record the actual project identifier only after creation.
4. Review text, scene order and any supported callouts, hotspots or navigation. Record
   supported and unavailable outputs separately; do not infer feature entitlement.
5. After a verified application change, recapture with ContextQA, compare matching
   sections and replace affected destination assets through supported controls.
6. Review the destination result before publishing under the client's approval policy.

If revising only the sample's wording/order, label that as a content revision, not an
application release. Do not substitute destination browser recording for ContextQA
execution in this lifecycle.

## Acceptance and remaining work

A native project must exist; the reviewed output must match ContextQA evidence; an
update must preserve working navigation and carry revision/instruction provenance.
Until those receipts exist, this folder remains a handoff runbook, not a runnable
sample. Native creation, update, export and publication automation remain unimplemented.

[Historical vendor reference](https://docs.layerpath.com/get-started/create-your-first-project)
— revalidate before implementation; not checked as part of this documentation update.
