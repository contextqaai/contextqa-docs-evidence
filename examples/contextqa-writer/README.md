# ContextQA-only documentation writer

This configuration maps the Kan board/list/card guide to the durable ContextQA case 186 and plan 39 in Ship 5. It is tenant-specific; do not run it against another tenant. The manifest maps source changes under `apps/web/**` to the guide. Saved credentials remain in ContextQA environment 1; no credentials or private recordings are included here.

Use [the writer instructions](../../agent-instructions/contextqa-writer.md) and [CLI workflow](../../docs/contextqa-writer.md). The current guide and comparison are private outputs because the recording contains the QA account identity. The source commit used in acceptance is `de9eb589ade097555b573473f9c833192d9af5a2`, deployed to `https://kan-qa.vercel.app` according to the user's attestation.

For another repository, replace the manifest mapping, create the documentation journeys through ContextQA, and register their actual definitions. An agent inspects the source change and ContextQA evidence, writes the structured guide, and finalizes the review. A plain terminal or coding agent is sufficient; no hosted app is required.

See the [live acceptance record](../../docs/contextqa-writer-acceptance.md) for passed runs, evidence resolution, failure history and scope.
