"""Stage real ContextQA editorial guides for hosted review using the selected destination."""

from pathlib import Path

from .. import agent, journeys
from ..core import Rejected
from ..loop import fingerprint
from .github_intake import BoundConnection
from .onboarding import admin, binding, setup
from .store import PostgresStore


def stage(pool, org, project, actor, plan, registry, exports, specs, *, delivery=None, discovery=None):
    if bool(delivery) == bool(discovery):
        raise Rejected("Choose one source delivery or discovery receipt")
    enriched = journeys.evidence_plan(plan, registry, exports)
    evidence = enriched["journey_evidence"]
    if not evidence or any(e["capture"]["execution"].get("transport") == "simulated" for e in evidence):
        raise Rejected("Real ContextQA journey evidence required")
    proposal = journeys.editorial_proposal(enriched, specs, exports)
    if proposal["questions"]:
        raise Rejected("Guide quality checks remain. Inspect the editorial proposal.")
    event = agent.validate_proposal(enriched, proposal)
    with pool.connection() as db:
        admin(db, org, actor)
        current = setup(db, org, project)
        if (
            not current["connected"]
            or plan["manifest"]["project_id"] != project
            or plan["manifest"]["repository"] != current["product_repo"]
        ):
            raise Rejected(
                "The selected project and connected product repository must match the source plan"
            )
        dest = {k: current[k] for k in ("docs_repo", "branch", "docs_root")}
        if delivery:
            row = db.execute(
                "SELECT revision,repository,destination,item_id FROM docs_source_deliveries WHERE organization_id=%s AND project_id=%s AND delivery=%s",
                (org, project, delivery),
            ).fetchone()
            if not row or tuple(row[:3]) != (plan["head_sha"], current["product_repo"], dest):
                raise Rejected("Source revision or destination differs from the recorded delivery")
            event["source_item_id"] = row[3]
        else:
            row = db.execute(
                "SELECT target_url FROM docs_discoveries WHERE id=%s AND organization_id=%s AND project_id=%s",
                (discovery, org, project),
            ).fetchone()
            if not row or row[0] != current["app_url"]:
                raise Rejected("Discovery target differs from the current app")
            event["discovery_id"] = str(discovery)
        workspace = binding(org, project).get("workspace_version_id")
        for entry in evidence:
            journey = journeys.select(registry, entry["journey_id"])
            if (
                journey["workspace_version_id"] != workspace
                or journey["application_url"] != current["app_url"]
            ):
                raise Rejected("Journey does not match this workspace and product URL")
            if not any(m["kind"] == "screenshot" for m in entry["capture"]["media"]):
                raise Rejected("A reviewed screenshot is required for every documented journey")
        event.update(documentation_destination=dest, requires_screenshots=True)
        event["id"] = "guide:" + fingerprint(event)
        store = PostgresStore(BoundConnection(db), org)
        if not event["edits"]:
            articles = store.snapshot(project, actor)["articles"]
            if any(articles.get(a["path"], {}).get("body", "") != a["before"] for a in plan["articles"]):
                raise Rejected("The hosted baseline changed before the no-change decision")
            return dict(status="no_change", review_required=False)
        result = store.ingest(project, actor, event)
        if not result["duplicate"]:
            for directory in exports.values():
                item = store.snapshot(project, actor)["items"][result["item_id"]]
                store.attach_evidence(project, actor, item["id"], item["version"], Path(directory))
        return dict(**result, status="awaiting_review", journeys=len(exports))


def deliver_guide(pool, org, project, actor, item, checkout, base_sha, journal_dir, confirmed):
    from ..loop_git import deliver

    if not confirmed:
        raise Rejected("Confirm creation of the reviewed draft PR")
    with pool.connection() as db:
        admin(db, org, actor)
        current = setup(db, org, project)
        destination = {k: current[k] for k in ("docs_repo", "branch", "docs_root")}
        previous = db.execute(
            """SELECT r.status,r.pr_url FROM docs_guide_prs r JOIN docs_projects p
               ON p.organization_id=r.organization_id AND p.id=r.project_id
               WHERE r.organization_id=%s AND r.project_id=%s AND r.item_id=%s
               AND r.approval_digest=(p.state->'items'->r.item_id->'approval'->>'digest')""",
            (org,project,item),
        ).fetchone()
        if previous:
            return dict(status=previous[0],url=previous[1],published=False)
        store = PostgresStore(BoundConnection(db), org)
        bundle = store.bundle(project, actor, item)
        if not current["connected"] or bundle["source"].get("documentation_destination") != destination:
            raise Rejected("Configure and review the intended documentation destination")
        key = (org, project, item, bundle["approval"]["digest"])
        db.execute(
            "INSERT INTO docs_guide_prs(organization_id, project_id, item_id, approval_digest, status) VALUES(%s,%s,%s,%s,'intent')",
            key,
        )
    branch = "contextqa-docs/" + item + "-" + key[-1][:12]
    # Persist intent before any remote write. Serialize disconnect against delivery.
    with pool.connection() as db:
        admin(db, org, actor)
        current = setup(db, org, project)
        if not current["connected"] or any(current[k] != v for k, v in destination.items()):
            raise Rejected("Connection changed before PR creation")
        receipt = deliver(
            bundle,
            checkout,
            destination["docs_repo"],
            base_sha,
            branch,
            Path(journal_dir) / (fingerprint(key) + ".jsonl"),
            approved=True,
            base_ref=destination["branch"],
            current_destination=destination,
        )
        db.execute(
            "UPDATE docs_guide_prs SET status='draft_pr_created',pr_url=%s WHERE organization_id=%s AND project_id=%s AND item_id=%s AND approval_digest=%s",
            (receipt["url"], *key),
        )
        return receipt
