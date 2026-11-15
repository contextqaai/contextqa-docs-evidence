# Local Salesforce landing-page drafts

Three landing pages plus eight readable guide pages. No hosting, analytics, forms, external scripts or destination publication. Draft pages carry noindex and use the unchanged canonical ContextQA logo.

From the repository root: `python3 -m http.server 8787 --bind 127.0.0.1`, then open `http://127.0.0.1:8787/site/salesforce/`. Serve only this sanitized repository; private context lives outside it. Stop the server after review.

Before publishing: confirm final URLs/navigation, destination owner, capability claims, media rights and current advisory dates. Remove noindex only as part of the approved publication. Course and scenarios are starters; no customer pass or finished video is implied.

Regenerate authored landing copy and HTML guide views with `python3 scripts/build-salesforce-site.py`; this also rebuilds the content-plan CSV. Edit guide source Markdown under docs/salesforce/guides. Validate local references with `python3 scripts/check-salesforce-content.py`. Neither command captures new application evidence or publishes a destination.
