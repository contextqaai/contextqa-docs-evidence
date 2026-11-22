"""Dispatch the documented ContextQA onboarding crawl through a dedicated tenant MCP session."""

import json
import re
from uuid import UUID, uuid4
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from psycopg.types.json import Jsonb

import anyio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr
from starlette.concurrency import run_in_threadpool

from .onboarding import PREFIX, admin, app_address, binding, expect_revision, setup


class CrawlRequest(BaseModel):
    revision: int = Field(ge=0)
    confirm: bool
    login_required: bool = False
    username: str = Field(default="", max_length=256)
    password: SecretStr | None = None


def response_text(result):
    return "\n".join(x.text for x in result.content if x.type == "text")


@asynccontextmanager
async def provider_session(config):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with httpx.AsyncClient(
        headers={"Authorization": "Bearer " + config["mcp_token"]},
        follow_redirects=False,
        timeout=15,
        trust_env=False,
    ) as http:
        async with streamable_http_client(config["mcp_url"], http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                identity = await session.call_tool("get_current_workspace", {})
                expected = str(config["workspace_version_id"])
                if identity.isError or not re.search(
                    r"\bworkspace_version_id=" + re.escape(expected) + r"\b", response_text(identity)
                ):
                    raise ValueError("Workspace mismatch")
                yield session


async def send_crawl(config, args, reserve):
    async with provider_session(config) as session:
        prior = await session.call_tool("manage_onboarding", {"action": "progress"})
        if prior.isError:
            raise ValueError("Cannot establish previous onboarding receipt")
        before = tool_data(prior).get("progress", {}).get("appDetails", {})
        ident, fresh = await run_in_threadpool(reserve)
        if not fresh:
            return ident, None
        result = await session.call_tool(
            "manage_onboarding", dict(action="app_details", confirm=True, **args)
        )
        if result.isError:
            return ident, ("needs_reconciliation", None, None, None, None)
        return ident, onboarding_receipt(before, tool_data(result))


def tool_data(result):
    raw = (result.structuredContent or {}).get("result") or response_text(result)
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def onboarding_receipt(before, data):
    step = data.get("appDetails") or {}
    job = data.get("jobId") or data.get("job_id") or data.get("generationJobId")
    job = str(job) if job and re.fullmatch(r"[\w-]{1,100}", str(job)) else None
    session = step.get("sessionId")
    session = (
        session if isinstance(session, str) and re.fullmatch(r"[a-fA-F0-9-]{36}", session) else None
    )
    case = step.get("runnerTestCaseId")
    requirement = step.get("uploadRequirementId")
    fresh_session = session and session != before.get("sessionId")
    return (
        "submitted" if job or fresh_session else "needs_reconciliation",
        job,
        case if type(case) is int else None,
        requirement if type(requirement) is int else None,
        session,
    )


def router(pool, auth):
    routes = APIRouter()

    @routes.post(PREFIX + "/discovery")
    async def start(org: str, project: str, body: CrawlRequest, actor=Depends(auth)):
        if not body.confirm:
            raise HTTPException(422, "Confirm the metered ContextQA crawl.")
        if body.login_required and (
            not body.username or not body.password or not body.password.get_secret_value()
        ):
            raise HTTPException(422, "Supply the dedicated test account login.")

        def check():
            with pool.connection() as db:
                admin(db, org, actor)
                current = setup(db, org, project)
                expect_revision(current, body.revision)
                if not current["description"]:
                    raise HTTPException(422, "Save the app description first.")
                return current

        current = await run_in_threadpool(check)
        config = binding(org, project)
        if (
            not all(config.get(k) for k in ("mcp_url", "mcp_token", "workspace_version_id", "app_url"))
            or config["app_url"] != current["app_url"]
        ):
            raise HTTPException(
                409, "Bind the saved app URL to its dedicated ContextQA workspace before crawling."
            )
        app_address(config["mcp_url"])
        args = dict(
            app_url=current["app_url"],
            description=current["description"],
            login_required=body.login_required,
        )
        if body.login_required:
            args.update(username=body.username, password=body.password.get_secret_value())
        reserved = []

        def reserve():
            with pool.connection() as db:
                admin(db, org, actor)
                expect_revision(setup(db, org, project), body.revision)
                values = (org, project, body.revision)
                old = db.execute(
                    "SELECT id FROM docs_discoveries WHERE organization_id=%s AND project_id=%s AND setup_revision=%s",
                    values,
                ).fetchone()
                if old:
                    return str(old[0]), False
                ident = str(uuid4())
                db.execute(
                    "INSERT INTO docs_discoveries(id,organization_id,project_id,setup_revision,status,target_url) VALUES(%s,%s,%s,%s,'awaiting_receipt',%s)",
                    (ident, *values, current["app_url"]),
                )
            reserved.append(ident)
            return ident, True

        try:
            with anyio.fail_after(50):
                ident, outcome = await send_crawl(config, args, reserve)
        except Exception:
            if not reserved:
                raise HTTPException(
                    503,
                    "ContextQA preflight failed. Verify the tenant connection and selected workspace.",
                ) from None
            ident, outcome = reserved[0], ("needs_reconciliation", None, None, None, None)

        def receipt():
            with pool.connection() as db:
                if outcome:
                    db.execute(
                        "UPDATE docs_discoveries SET status=%s,provider_job=%s,provider_case=%s,provider_requirement=%s,provider_session=%s WHERE id=%s",
                        (*outcome, ident),
                    )
                status, job = db.execute(
                    "SELECT status,provider_job FROM docs_discoveries WHERE id=%s", (ident,)
                ).fetchone()
                return dict(id=ident, status=status, provider_job=job)

        return await run_in_threadpool(receipt)

    @routes.post(PREFIX + "/discovery/{ident}/refresh")
    async def refresh(org: str, project: str, ident: UUID, actor=Depends(auth)):
        def read():
            with pool.connection() as db:
                admin(db, org, actor)
                row = db.execute(
                    """SELECT target_url,status,provider_session,provider_case,created_at,evidence_receipt
                    FROM docs_discoveries WHERE organization_id=%s AND project_id=%s AND id=%s""",
                    (org, project, ident),
                ).fetchone()
                if not row:
                    raise HTTPException(404, "Discovery unavailable.")
                return row

        target, status, session_id, case_id, created, existing = await run_in_threadpool(read)
        if existing:
            return existing
        if not session_id or not case_id:
            return {"status": status, "detail": "No attributable runner session yet."}
        config = binding(org, project)
        if config.get("app_url") != target:
            raise HTTPException(409, "The bound app URL changed.")
        try:
            with anyio.fail_after(30):
                async with provider_session(config) as client:
                    res = await client.call_tool(
                        "get_execution_status", dict(session_id=session_id, wait=False)
                    )
                    if res.isError:
                        raise ValueError
                    run = tool_data(res)
                    if not run.get("is_completed"):
                        return {"status": status, "detail": "Awaiting a completed ContextQA execution."}
                    started = datetime.fromisoformat(str(run["started_at"]).replace("Z", "+00:00"))
                    if (
                        str(run.get("test_case_id")) != str(case_id)
                        or run.get("session_id") != session_id
                        or started < created - timedelta(minutes=1)
                    ):
                        return {
                            "status": "needs_reconciliation",
                            "detail": "The returned execution does not match this submission.",
                        }
                    result_id = int(run["result_id"])
                    res = await client.call_tool("get_execution_step_details", dict(result_id=result_id))
                    if res.isError:
                        raise ValueError
                    steps = tool_data(res)
                    if steps.get("result_id") != result_id:
                        raise ValueError
                    passed = steps.get("overall_result") == "SUCCESS"
                    receipt = dict(
                        status="execution_passed" if passed else "execution_failed",
                        case_id=case_id,
                        result_id=result_id,
                        step_result_ids=[s["step_result_id"] for s in steps.get("steps", [])],
                        recordings=len(steps.get("screen_recordings") or []),
                        deployment_verified=False,
                    )
        except Exception:
            raise HTTPException(
                502, "Unable to reconcile the ContextQA execution. Check the same receipt again."
            ) from None

        def save():
            with pool.connection() as db:
                admin(db, org, actor)
                db.execute(
                    "UPDATE docs_discoveries SET status=%s,evidence_receipt=%s WHERE id=%s",
                    (receipt["status"], Jsonb(receipt), ident),
                )

        await run_in_threadpool(save)
        return receipt

    return routes
