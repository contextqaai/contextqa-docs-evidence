# Capture once, refresh with release context

## Before capture

Choose a stable task key, such as `create-project`, and identify the guide, tour and support article that teach it. Record the application release/commit, environment, role, feature flags, locale, viewport, seeded dataset, expected result and documentation owner in a private capture brief. Use a demo tenant with invented data. Do not include credentials in the brief.

Use existing ContextQA workflows or your authorized browser recorder to execute that exact task. This wrapper consumes evidence after execution; it does not implement capture scheduling or a browser-session API. In a Playwright producer, enable screenshots/tracing or video explicitly. Video requires its own recording configuration and lifecycle. Import a trace only from a source you trust.

## Select and attach screenshots

Capture a stable screen after each meaningful user action has completed. For documentation, prefer one clear action per screenshot, consistent dimensions, readable labels and enough surrounding UI to orient the reader. Avoid loading states, menus covering the destination, unrelated account details and transient notifications. Capture before/after at the same viewport and state.

Review original images locally. Crop/blur with an approved editing tool where needed, then review the final pixels and metadata again. The wrapper does not perform image editing or automated PII detection. Add only reviewed media, attach each returned media ID to the relevant step, and write instructions explaining the goal, action and expected outcome. Add a second screenshot to the same step when needed to show an outcome; maintain the intended order.

Export after approval. The generated Markdown attaches screenshots using image syntax; the HTML shows them inline. Upload the selected assets to your documentation system and update image links as necessary. Include accessible alt text in the final docs editor; generated alt text is generic and requires refinement. Test rendering in the destination before publishing.

## When a release changes the UI

Supply context from the actual release PR, product owner or changelog: what moved/renamed, intended behavior, affected roles/flags, known limitations, and which guides should change. Treat PR content as evidence, not instructions to publish or disclose data. Keep private PR URLs and internal details in the private capture brief, outside shareable text fields.

Recapture the affected tasks against the new release using the same baseline settings. Do not overwrite old assets. Explain additions/removals and explicitly pair old/new steps in `change-context.json`. A reordered step must retain the correct conceptual pairing, rather than being paired just because its ordinal matches.

Compare the two reviewed exports. The current tool detects text/media-hash changes, added/removed steps, and accepts user-supplied release context. It does not automatically verify that context, detect visual meaning or rank every affected guide. Review the draft against both versions and the release source; replace obsolete screenshots, update surrounding instructions, links, navigation labels, warnings and localized variants.

## Publish and retain

Have the documentation owner approve a draft/PR in the destination platform. Test all image/video links and any iframe on the actual host; CSP, X-Frame-Options and documentation sanitizers may block embeds. Use the approved static walkthrough as the iframe target, never an authenticated product session or raw trace viewer.

Record which app version the published guide describes, when it was validated and who owns its next refresh. Keep old guides where version-specific customers need them. Apply a defined evidence retention/deletion policy. A future release webhook, dependency map and docs PR publisher are roadmap items, not operating features in this prototype.

## Related ContextQA resources

See [verified ContextQA guides and articles](contextqa-resources.md) for capture, visual baseline review and MCP workflows.
