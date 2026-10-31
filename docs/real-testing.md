# Install and test a real screenshot walkthrough

This guide tests the installed Python package and a complete local media lifecycle: capture → inspect and review → attach → export → make a controlled change → recapture → compare → inspect the resulting guide. It needs no ContextQA account, AI key, paid service or partner login. Browser capture is performed by an authorized producer or a person; this wrapper does not drive the browser.

## What the existing successful CI proves

The October 27, 2026 private-push verification receipt records commit `6a437e905dfc989208ac94019155b50172754223` and successful [Actions run 40601776459](https://github.com/contextqaai/contextqa-docs-evidence/actions/runs/40601776459). That receipt was based on GitHub UI verification. The workflow has three jobs:

| Check | Actual scope | What it does not establish |
|---|---|---|
| Python 3.12 and 3.13 | Each runs the 30 Python unit/security checks and `examples/demo.py`. Tests cover review/digest enforcement, export boundaries, trace safety, result-parent checks, comparison mapping and AI-input extraction. | No package installation, actual screenshot capture, native partner session or live ContextQA request. Media fixtures include header-shaped synthetic bytes; they are not decoded screenshots of a real UI. |
| Node 22 AI | Runs the 10 provider/consent/usage tests using mocked transports. | No real OpenAI, Anthropic or compatible-provider request, credential validation, billed usage or generated-content quality test. |
| Text-only demo within both Python jobs | Creates two synthetic text walkthroughs, reviews/exports them and compares explicitly mapped steps. | No browser, images, video, observed application behavior or Layerpath/EkLine publication. |

A successful workflow is useful evidence within this scope. It is not proof of a real-media lifecycle or a hosted integration. The separate procedure below closes the installed-package and media/rendering gaps; record its actual outcome separately rather than relabeling the old run.

## 1. Install into a disposable environment

Use Python 3.10+ and a POSIX shell on macOS/Linux. The package declares no runtime dependencies. A normal pip build may obtain its declared `setuptools` build requirement. Node 22+ is needed only for the separate optional AI checks.

From the repository directory:

```sh
CQA_REPO="$PWD"
CQA_CHECK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/cqa-docs-evidence.XXXXXX")
python3 -m venv "$CQA_CHECK_ROOT/venv"
CQA_PY="$CQA_CHECK_ROOT/venv/bin/python"
CQA_CLI="$CQA_CHECK_ROOT/venv/bin/cqa-artifacts"
"$CQA_PY" -m pip install --no-deps "$CQA_REPO"
cd "$CQA_CHECK_ROOT"
"$CQA_PY" -I -c 'import sys; from pathlib import Path; from importlib.metadata import version; import cqa_artifacts.core as core; assert Path(core.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()); print(version("contextqa-artifact-wrapper")); print(core.__file__)'
"$CQA_CLI" --help
```

This is a regular, non-editable install. Running from the new directory with isolated import mode checks that Python loads the installed package rather than accidentally importing the checkout. Keep this terminal open so the variables remain available.

Run the source regression suite separately; these tests intentionally execute from the checkout:

```sh
cd "$CQA_REPO"
"$CQA_PY" -m unittest discover -s tests -v
"$CQA_PY" examples/demo.py "$CQA_CHECK_ROOT/text-demo"
npm run test:ai
cd "$CQA_CHECK_ROOT"
```

The last command is optional if Node is unavailable. None of these checks requires an AI key. Record actual versions, test totals and failures; counts may change in later commits.

## 2. Capture an actual screen for version A

Choose a disposable local demo with invented data. One available producer is the companion [ContextQA Browser Cloud pilot](https://github.com/contextqaai/contextqa-browser-cloud): follow its local setup, open its loopback console, start a demo session, run its demo task, save a screenshot and download the PNG. End the session to release the browser. Its local demo does not require a customer account or hosted ContextQA token. Do not enable external targets merely to follow this guide.

An existing authorized capture producer or your operating system's screenshot tool is also suitable. Capture the **actual application content**, not a screenshot of a code sample or an invented byte fixture. Wait for the relevant task to finish. Use the same viewport, role, locale and seeded data when recapturing. Review the producer's own result separately: a screenshot alone does not prove an assertion passed.

Save the image outside Git as `$CQA_CHECK_ROOT/capture-a.png`. If it is JPEG/WebP, use its actual extension throughout. Do not just rename an unsupported file to PNG.

Record a private capture brief containing the task, target, version label, timestamp, viewport, data/role, actions actually performed, observed outcome and any failure. For this exercise use a label such as **controlled sample A**, not an unsupported claim about a product release. Do not put credentials, signed URLs or personal data into the guide text.

Before continuing, open the original image locally and inspect all pixels and file metadata. Confirm rights to use/share it and absence of private content. Crop or redact with an approved tool when necessary, then inspect the final image again. The wrapper's header check does not sanitize, fully decode or certify media.

## 3. Build, review and export A

Write instructions that accurately match the captured action and outcome. The text below assumes a synthetic project-creation flow; replace it with what was actually observed.

```sh
"$CQA_CLI" init "$CQA_CHECK_ROOT/workspace-a" --title 'Controlled sample A — create a project'
"$CQA_CLI" add-step "$CQA_CHECK_ROOT/workspace-a" --title 'Create the sample project' --instruction 'Select Projects, choose Create project, enter the invented sample name, and confirm the project opens.'
CQA_MEDIA_A=$("$CQA_CLI" add-media "$CQA_CHECK_ROOT/workspace-a" --kind screenshot --file "$CQA_CHECK_ROOT/capture-a.png" | "$CQA_PY" -c 'import json,sys; print(json.load(sys.stdin)["media_id"])')
"$CQA_CLI" attach "$CQA_CHECK_ROOT/workspace-a" --step 1 --media-id "$CQA_MEDIA_A"
"$CQA_CLI" inspect "$CQA_CHECK_ROOT/workspace-a"
```

Inspect `workspace-a/manifest.json`, the selected image and the capture brief together. Verify the instruction's factual accuracy and selected media. Only after a person has completed the content/media/rights review:

```sh
"$CQA_CLI" approve "$CQA_CHECK_ROOT/workspace-a" --reviewer 'YOUR REVIEWER NAME' --confirm-rights-and-reviewed-content
"$CQA_CLI" export "$CQA_CHECK_ROOT/workspace-a" --out "$CQA_CHECK_ROOT/export-a" --base-url https://docs.example.com/local-acceptance/a
```

Replace the reviewer name; do not treat an example command as an automatic approval. The HTTPS URL only constructs a future iframe snippet. Nothing is hosted or uploaded, and `docs.example.com` is not a working destination.

## 4. Make a controlled change, capture and export B

Make one permitted change in the disposable demo, such as a deliberately revised sample project name or an editable demo label. Record exactly what changed. A changed seeded value is a **content revision**, not evidence of a real application release. If you cannot safely change the target, use an owner-provided second demo version; do not invent a change.

Repeat the same task and capture the completed state as `$CQA_CHECK_ROOT/capture-b.png`. Review B's original pixels/metadata and record a separate timestamp/outcome. Never overwrite A. If only content changed, preserve the navigation instructions and describe the actual content change; do not falsely claim a renamed button.

```sh
"$CQA_CLI" init "$CQA_CHECK_ROOT/workspace-b" --title 'Controlled sample B — create a project'
"$CQA_CLI" add-step "$CQA_CHECK_ROOT/workspace-b" --title 'Create the revised sample project' --instruction 'Repeat the approved project-creation task using the revised invented sample name and confirm that project opens.'
CQA_MEDIA_B=$("$CQA_CLI" add-media "$CQA_CHECK_ROOT/workspace-b" --kind screenshot --file "$CQA_CHECK_ROOT/capture-b.png" | "$CQA_PY" -c 'import json,sys; print(json.load(sys.stdin)["media_id"])')
"$CQA_CLI" attach "$CQA_CHECK_ROOT/workspace-b" --step 1 --media-id "$CQA_MEDIA_B"
"$CQA_CLI" inspect "$CQA_CHECK_ROOT/workspace-b"
```

Perform the same human review, then:

```sh
"$CQA_CLI" approve "$CQA_CHECK_ROOT/workspace-b" --reviewer 'YOUR REVIEWER NAME' --confirm-rights-and-reviewed-content
"$CQA_CLI" export "$CQA_CHECK_ROOT/workspace-b" --out "$CQA_CHECK_ROOT/export-b" --base-url https://docs.example.com/local-acceptance/b
cat > "$CQA_CHECK_ROOT/change-context.json" <<'JSON'
{
  "before_version": "controlled sample A",
  "after_version": "controlled sample B",
  "what_changed": "The invented sample project name was changed in the disposable demo. This is a controlled content revision, not a product release.",
  "affected_documents": "Local sample project-creation guide",
  "step_pairs": [{"before": 1, "after": 1}]
}
JSON
"$CQA_CLI" compare "$CQA_CHECK_ROOT/export-a" --after "$CQA_CHECK_ROOT/export-b" --context "$CQA_CHECK_ROOT/change-context.json" --out "$CQA_CHECK_ROOT/change-review"
```

Edit the change explanation to match reality. Every old/new step must appear exactly once in the mapping. Use `null` for an added or removed step. Pair reordered steps by meaning, not position. Comparison detects text/media identity changes; it does not verify release claims or perform semantic/pixel regression testing.

## 5. Verify the resulting files and browser rendering

Run this against the installed package from the disposable directory:

```sh
"$CQA_PY" -I - "$CQA_CHECK_ROOT" <<'PY'
import json
from pathlib import Path
import sys
from cqa_artifacts.changes import reviewed

root = Path(sys.argv[1])
for label in ("a", "b"):
    folder = root / ("export-" + label)
    data = reviewed(folder)
    assert len(data["steps"]) == 1 and len(data["media"]) == 1
    assert data["steps"][0]["media"] == [data["media"][0]["id"]]
    asset = data["media"][0]["path"]
    assert (folder / asset).is_file()
    page = (folder / "index.html").read_text()
    guide = (folder / "guide.md").read_text()
    assert '<img src="' + asset + '"' in page
    assert "![screenshot for step 1](" + asset + ")" in guide
    assert not (folder / "private").exists()
    print("Open in browser:", (folder / "index.html").as_uri())
report = json.loads((root / "change-review" / "changes.json").read_text())
assert len(report["steps"]) == 1
assert report["steps"][0]["status"] == "changed"
assert "Before" in (root / "change-review" / "index.html").read_text()
assert "After" in (root / "change-review" / "index.html").read_text()
print("Open comparison:", (root / "change-review" / "index.html").as_uri())
print("File, media-digest and review-receipt checks passed; inspect rendering manually.")
PY
```

Open the printed local HTML URLs in a browser. Confirm the actual screenshot decodes, is readable, matches the instructions, preserves the intended order and displays in both before/after sections. Open each `guide.md` in a Markdown preview and confirm its relative image resolves. Check the comparison's change explanation against the capture briefs. A file/link check cannot establish visual rendering, so record both checks separately.

Do not call this a verified test result unless a separate producer supplied successful assertions. This acceptance test establishes that real reviewed screenshots can be packaged and refreshed. It does not establish that every documented business rule is correct.

## Failure checks and troubleshooting

- **Missing review or changed text/media:** export/compare must fail. Preserve the old baseline, review the change and approve again. Do not edit the receipt digest to bypass review. Unit tests already cover this failure path.
- **Output already exists:** choose a new export/comparison path. The tool refuses mixing or overwriting prior data.
- **No screenshot in HTML:** confirm `add-media` returned an ID and that ID was attached to the intended step. An unattached image is intentionally excluded.
- **Broken Markdown image in another docs system:** upload only approved assets and rewrite relative paths for that destination. Local success does not verify remote asset hosting.
- **Unreadable media:** decode/open the original before import. Magic-header acceptance alone is insufficient.
- **Changed report says unchanged:** ensure the controlled input or selected screenshot actually differs; do not fabricate a change merely to satisfy the example. Adjust the expected report to the observed case.
- **Package command imports checkout:** repeat the normal install and isolated import check from a directory outside the checkout. An editable install/source-only test does not close this gap.

## Keep live checks separate

`collect` is an optional read of explicitly selected **existing** ContextQA result records. It needs an authorized scoped token and run ID; it does not trigger execution or download all remote artifacts. A live read is not exercised by the checks above. The new `contextqa-run --approve-execution` path implements a journalled saved-plan trigger and may bill; its tests use transport mocks, not a live start. It is outside this account-free media procedure. See [API usage and exact guardrails](contextqa-api.md). Do not retry a potentially accepted upstream start or infer cancellation from a timeout. See [capability register](capability-register.md).

Trace screenshot compatibility is checked separately from direct PNG attachment. A real Playwright 1.64.1 trace exposed newer `screencast-frame.file` references to flat `screencast/...jpeg` ZIP members, rather than the older `sha1` plus `resources/...` layout. The importer supports both explicit shapes, rejects arbitrary/nested/traversing file references and retains its archive/path/size safeguards. Added regression tests cover both layouts, repeated frames and hostile references. Imported frames remain unattached review candidates; frame extraction is not a video or a passing test. Internal trace formats may change again; a missing/unsupported frame is a compatibility gap to report, not evidence that capture succeeded.

`prepare-ai-input.py` extracts only text from an unchanged reviewed export. Its tests do not prove that visible human-authored text is free of private information. Model calls require separate exact-file sharing consent and can incur provider charges. [AI instructions and limits](ai.md). Neither real-provider keys nor native Layerpath/EkLine access is needed for this guide; those remain separate acceptance tasks.

Keep a private acceptance receipt with commit, runtime/package versions, installed module path, exact commands, test totals, capture timestamps and hashes, controlled change, human reviewer confirmation, rendering checks and any failures. Separate `package-installed`, `unit-tests-passed`, `real-media-lifecycle-passed`, `live-api-read-tested`, `live-ai-tested` and `native-partner-tested` fields. Leave unperformed checks false or unknown. Do not commit actual customer evidence, tokens, raw traces or private briefs. Local success does not authorize uploading or publishing the artifacts.

## Observed media acceptance — October27,2026

A regular wheel install in a fresh Python3.14.2 environment exercised the installed command outside the checkout. Two actual1280×800 synthetic browser screenshots produced a reviewed Markdown/HTML guide; both images rendered and Next navigation worked. Before/after comparison rendered all4image references and identified1changed paired step. Editing the private workspace after approval blocked export. A real Playwright1.64.1 trace initially exposed the frame-compatibility gap; after reinstalling the fix it imported2actions and5frame events (4unique images) as unattached review candidates. The [observed walkthrough example](../examples/observed-browser-walkthrough/README.md) contains only reviewed synthetic exports; raw video/trace and credentials are excluded. This does not prove a live SaaS or native partner workflow.

## ContextQA adapter validation added October 27

The new adapter adds mocked authoring, project preflight, journalled saved-plan start, bounded polling and selected result-to-guide tests. Run `python3 examples/contextqa_demo.py NEW_OUTPUT` for an explicitly simulated end-to-end API workflow. [The current adapter validation receipt](contextqa-validation-receipt.json) separates unit/mock tests and outside-checkout installed CLI checks from live tenant acceptance. No live token, billed plan start or real provider call is part of these checks. Follow [ContextQA API instructions](contextqa-api.md) only after the applicable target/data/cost boundary is approved.
