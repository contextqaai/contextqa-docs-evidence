import argparse
import json
import os
from pathlib import Path
import sys
from . import core


def main():
    parser = argparse.ArgumentParser(description="ContextQA workflow evidence; live writes and billed saved-plan starts require explicit opt-in")
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
    sub.add_parser("contextqa-operations", help="List implemented contract operation IDs and scopes; no account needed")
    p = sub.add_parser("contextqa-call")
    p.add_argument("--operation", required=True)
    p.add_argument("--id", type=int)
    p.add_argument("--query", type=Path)
    p.add_argument("--body", type=Path)
    p.add_argument("--approve-write", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("contextqa-run")
    p.add_argument("--plan-id", type=int, required=True)
    p.add_argument("--environment")
    p.add_argument("--journal", type=Path, required=True)
    p.add_argument("--approve-execution", action="store_true")
    p.add_argument("--profile", type=Path, help="Read and check approved project config before the single start")
    p = sub.add_parser("contextqa-project-check")
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("contextqa-poll")
    selection = p.add_mutually_exclusive_group(required=True)
    selection.add_argument("--run-id", type=int)
    selection.add_argument("--journal", type=Path)
    p.add_argument("--max-attempts", type=int, default=20)
    p.add_argument("--interval", type=float, default=2)
    p.add_argument("--deadline", type=float, default=60)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("contextqa-collect")
    p.add_argument("workspace", type=Path)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--plan-id", type=int)
    p.add_argument("--profile", type=Path)
    p.add_argument("--case-result-id", type=int, action="append", default=[])
    p.add_argument("--step-result-id", type=int, action="append", default=[])
    p.add_argument("--suite-result-id", type=int, action="append", default=[])
    p.add_argument("--import-steps", action="store_true")
    args = parser.parse_args()
    root = getattr(args, "workspace", None)
    command = args.command
    if command.startswith("contextqa-"):
        from . import contextqa as api
        if command == "contextqa-operations":
            result = {name: {key: op[key] for key in ("method", "path", "permission")} for name, op in api.OPERATIONS.items()}
        else:
            client = api.ContextQAClient(os.environ.get("CONTEXTQA_API_TOKEN"))
            if command == "contextqa-call":
                result = client.call_to_file(args.operation, args.out, id=args.id, query=core.load_json(args.query) if args.query else None,
                                             body=core.load_json(args.body) if args.body else None, approve_write=args.approve_write)
            elif command == "contextqa-run":
                if not args.approve_execution:
                    raise core.Rejected("Saved-plan execution may bill; explicit --approve-execution is required")
                preflight = None
                environment = args.environment
                if args.profile:
                    from .project import inspect_project
                    profile = core.load_json(args.profile)
                    if profile.get("plan", {}).get("id") != args.plan_id:
                        raise core.Rejected("Profile plan ID must match --plan-id")
                    query = profile.get("execution", {}).get("query", {})
                    if any(key != "environment" for key in query):
                        raise core.Rejected("This documentation run supports only an approved environment query; no mobile build trigger")
                    if environment is not None and environment != query.get("environment"):
                        raise core.Rejected("Explicit environment conflicts with the approved project profile")
                    environment = query.get("environment")
                    preflight = inspect_project(client, profile)
                result = client.trigger_run(args.plan_id, args.journal, approve_execution=args.approve_execution, environment=environment, preflight=preflight)
            elif command == "contextqa-project-check":
                from .project import inspect_project
                api.exclusive_json(args.out, {"state": "project_check_intent"})
                checked = inspect_project(client, core.load_json(args.profile))
                api.replace_private_json(args.out, checked)
                result = {key: checked[key] for key in ("checked", "planId", "profileSha256", "observedSha256", "paidExecutionStarted")}
            elif command == "contextqa-poll":
                run_id = api.recorded_run(args.journal) if args.journal else args.run_id
                data = client.poll_run(run_id, max_attempts=args.max_attempts, interval=args.interval, deadline=args.deadline)
                api.exclusive_json(args.out, data)
                result = {key: data[key] for key in ("run_id", "attempts", "verdict", "polling_stopped", "upstream_cancelled")}
            else:
                result = api.collect_results(client, root, args.run_id, args.case_result_id, args.step_result_id, args.suite_result_id,
                                             plan_id=args.plan_id, profile=core.load_json(args.profile) if args.profile else None)
                if args.import_steps:
                    result["guide_import"] = api.import_result_steps(root)
    elif command == "compare":
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
    if command == "contextqa-poll" and result["verdict"] != "passed":
        raise SystemExit(2)


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
