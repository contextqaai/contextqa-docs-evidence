import argparse
import json
import os
from pathlib import Path
import sys
from . import core


def main():
    parser = argparse.ArgumentParser(description="Private-first ContextQA evidence wrapper; no browser or paid-run execution")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["init", "add-step", "edit-step", "add-media", "attach", "import-trace", "collect", "approve", "export", "inspect"]:
        p = sub.add_parser(name)
        p.add_argument("workspace", type=Path)
        if name == "init":
            p.add_argument("--title", required=True)
        if name in ("add-step", "edit-step"):
            p.add_argument("--title", required=True)
            p.add_argument("--instruction", required=True)
        if name in ("edit-step", "attach"):
            p.add_argument("--step", type=int, required=True)
        if name == "add-media":
            p.add_argument("--file", type=Path, required=True)
            p.add_argument("--kind", choices=["screenshot", "video"], required=True)
        if name == "attach":
            p.add_argument("--media-id", required=True)
        if name == "import-trace":
            p.add_argument("--file", type=Path, required=True)
        if name == "collect":
            p.add_argument("--run-id", type=int, required=True)
            p.add_argument("--case-result-id", type=int, action="append", default=[])
            p.add_argument("--step-result-id", type=int, action="append", default=[])
        if name == "approve":
            p.add_argument("--reviewer", required=True)
            p.add_argument("--confirm-rights-and-reviewed-content", action="store_true")
        if name == "export":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--base-url", required=True, help="Future HTTPS hosting path, not an upload destination")
    p = sub.add_parser("compare")
    p.add_argument("workspace", type=Path, help="Reviewed before export")
    p.add_argument("--after", type=Path, required=True)
    p.add_argument("--context", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace
    command = args.command
    if command == "compare":
        from .changes import compare
        result = compare(root, args.after, args.context, args.out)
    elif command == "init":
        core.init(root, args.title)
        result = {"created": True, "private_by_default": True}
    elif command == "add-step":
        core.add_step(root, args.title, args.instruction)
        result = {"added": True}
    elif command == "edit-step":
        core.edit_step(root, args.step, args.title, args.instruction)
        result = {"updated": True}
    elif command == "add-media":
        result = {"media_id": core.add_media(root, args.file, args.kind), "requires_review": True}
    elif command == "attach":
        core.attach(root, args.step, args.media_id)
        result = {"attached": True}
    elif command == "import-trace":
        result = core.import_trace(root, args.file)
    elif command == "collect":
        token = os.environ.get("CONTEXTQA_API_TOKEN")
        if not token:
            raise core.Rejected("Set CONTEXTQA_API_TOKEN through your secret manager or local environment; never a CLI argument")
        result = core.collect(root, token, args.run_id, args.case_result_id, args.step_result_id)
    elif command == "approve":
        result = {"approved_digest": core.approve(root, args.reviewer, args.confirm_rights_and_reviewed_content)}
    elif command == "export":
        result = core.export(root, args.out, args.base_url)
    else:
        data = core.manifest(root)
        # Intentionally omit paths, raw API data and reference URLs from terminal receipts.
        result = {"steps": len(data["steps"]), "media": len(data["media"]), "approval_file_present": (root / "approval.json").exists(), "steps_needing_review": sum(s.get("needs_review", False) for s in data["steps"])}
    print(json.dumps(result))


def cli():
    try:
        main()
    except Exception as error:
        # Do not echo raw upstream bodies, URLs, credential values, or arbitrary input.
        message = str(error) if isinstance(error, core.Rejected) else "Input or filesystem operation failed; inspect local inputs privately"
        print(json.dumps({"error": message}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
