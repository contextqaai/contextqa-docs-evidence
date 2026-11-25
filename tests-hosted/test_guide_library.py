"""Isolated, synthetic contract fixtures for publication, access, media and refresh."""

import io
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from PIL import Image
from psycopg.types.json import Jsonb
from cqa_artifacts import core, journeys
from cqa_artifacts.changes import reviewed
from cqa_artifacts.loop import fingerprint
from cqa_artifacts.hosted.media_editor import Box, transform
from cqa_artifacts.hosted import refresh
from test_editorial_review import HostedFixture


class GuideLibraryTests(HostedFixture):
    def verified_fixture(self):
        # Synthetic provider response, including the API transport field, for contract verification only.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        work = Path(tmp.name) / "source"
        export = Path(tmp.name) / "reviewed"
        core.init(work, "Test capture")
        core.add_step(work, "Open invitations", "Open Invitations.")
        buf = io.BytesIO()
        Image.new("RGB", (16, 16), "red").save(buf, format="PNG")
        media = core.add_media_bytes(work, buf.getvalue(), "screenshot")
        core.attach(work, 1, media)
        data = core.manifest(work)
        sha = "1" * 40
        src = "a" * 64
        data["steps"][0].update(case_result_id=400, step_result_id=401)
        data["execution"] = dict(
            run_id=40,
            transport="ContextQA API",
            collected_at="2026-11-20T00:00:00Z",
            status="STATUS_COMPLETED",
            result="SUCCESS",
            verdict="passed",
            case_result_ids=[400],
            step_result_ids=[401],
            source_sha256=src,
            media_downloaded=False,
        )
        data["capture_context"] = dict(commit_sha=sha, workflow_id="invites")
        core.save(work, data)
        core.approve(work, "Fixture editor", True)
        core.export(work, export, "https://example.org")
        digest = fingerprint(reviewed(export))
        core.write_json(
            export / "journey-review.json",
            journeys.sealed(
                dict(
                    evidence_policy="contextqa-only-v1",
                    export_digest=digest,
                    source_sha256=src,
                    journey_id="invites",
                    run_id=40,
                    head_sha=sha,
                    deployment=dict(confirmed=True, commit_sha=sha, run_id=40),
                    media_origins=[dict(media_id=media, step_result_id=401)],
                )
            ),
        )
        return export, digest, media, sha

    def test_reviewed_capture_generates_deliverable_tutorial(self):
        import shutil

        export, digest, mid, sha = self.verified_fixture()
        registry = json.loads(
            (Path(__file__).resolve().parents[1] / "examples/kan-pr15/journeys.json").read_text()
        )
        journey = registry["journeys"][0]
        journey.update(id="invites", required_media=["screenshot"])
        registry["journeys"] = [journey]
        job = uuid4()
        root = export.parent / "capture-jobs"
        saved = root / str(job) / "reviewed"
        shutil.copytree(export, saved)
        file = saved / "journey-review.json"
        receipt = journeys.checked(core.load_json(file))
        receipt["deployment"].update(
            application_url=journey["application_url"], environment=journey["environment"],
            journey_digest=fingerprint(journey), verified_by="fixture-deployer",
            evidence_ref="fixture-deployment",
        )
        core.write_json(file, journeys.sealed(receipt))
        with self.pool.connection() as db:
            db.execute(
                """INSERT INTO docs_capture_jobs(id,organization_id,project_id,request_id,journey,
                digest,registry,revision,status,provider_run) VALUES(%s,%s,'docs',%s,'invites',%s,%s,%s,'reviewed',40)""",
                (job, self.org, job, fingerprint(registry), Jsonb(registry), sha),
            )
        brief = dict(self.brief, template="Tutorial", capture=str(job))
        item = self.create(requires_screenshots=True, revision=sha)
        with patch("cqa_artifacts.hosted.editorial.private_root", return_value=root):
            self.write(self.create(revision="9" * 40), "generate", brief, code=409)
            self.write(item, "generate", brief)
        article = self.item(item)["changes"][0]["after"]
        self.assertIn("Open Invitations", article)
        self.assertIn(mid + ".png", article)
        figure = self.api.get(self.base + f"writing/{item}/figures/{digest}/{mid}")
        self.assertEqual(figure.status_code, 200)
        self.assertEqual(hashlib.sha256(figure.content).hexdigest(), mid)
        for action in ("accept_item", "ready"):
            self.store.review("docs", "owner", item, self.item(item)["version"], action)
        self.store.approve("docs", "owner", item, self.item(item)["version"], True)
        result = self.api.post(self.base + "library/save", json=dict(
            item=item, version=self.item(item)["version"], expected_heads={self.path: None}
        ))
        self.assertEqual(result.status_code, 200, result.text)
        version = result.json()["versions"][self.path]
        detail = self.api.get(self.base + "library/version", params=dict(path=self.path, digest=version)).json()
        self.assertEqual(detail["body"], article)
        self.assertEqual((detail["media"][0]["run"], detail["media"][0]["step"]), (40, 401))

    def test_walkthrough_uses_scoped_saved_edition(self):
        _, digest, media_id = self.library_save()
        endpoint = self.base + "library/walkthrough"
        params = dict(path=self.path, digest=digest)
        response = self.api.get(endpoint, params=params)
        self.assertEqual(response.status_code, 200)
        first, = response.json()["scenes"]
        self.assertEqual((first["digest"], first["run"], first["step"]), (media_id, 40, 401))
        self.assertEqual(self.api.get(endpoint, params={**params, "digest": "old"}).status_code, 404)
        self.assertEqual(self.client("writer").get(endpoint, params=params).status_code, 403)

    def test_walkthrough_shows_only_visible_traceable_scenes_in_article_order(self):
        from cqa_artifacts.hosted.walkthrough import walkthrough_scenes
        folder = "evidence/" + "a" * 64 + "/assets/"
        photo = folder + "b" * 64 + ".png"
        clip = folder + "c" * 64 + ".webm"
        media = [
            dict(path=ref, digest=digest * 64, kind=kind, run=1, step=2, journey="review", revision="build")
            for ref, digest, kind in [(photo, "b", "screenshot"), (clip, "c", "video")]
        ]
        image = f"![Open **inbox**](../{photo})"
        video = f"[Watch](../{clip})"
        body = f"{video}\n\n{image}\n\n<!-- {image} -->\n\n~~~md\n{image}\n~~~\n\n[External](https://example.org/{photo})"
        result = walkthrough_scenes("guides/review.md", body, media)
        self.assertEqual([s["caption"] for s in result], ["Watch", "Open inbox"])
        for key in ("digest", "run", "step", "revision", "journey", "kind"):
            self.assertEqual(walkthrough_scenes("guides/review.md", image, [{**media[0], key: ""}]), [])

    def test_hidden_evidence_links_do_not_illustrate_a_guide(self):
        from cqa_artifacts.editions import media_dependencies

        target = "../evidence/" + "a" * 64 + "/assets/" + "b" * 64 + ".png"
        figure = "![Invitations](" + target + ")"
        for text in ["<!--\n" + figure + "\n-->", "    " + figure, "~~~md\n" + figure + "\n~~~"]:
            self.assertEqual(media_dependencies(self.path, text), [])
        self.assertEqual(len(media_dependencies(self.path, figure)), 1)

    def request_with_evidence(self):
        export, digest, media, sha = self.verified_fixture()
        link = "../evidence/" + digest + "/assets/" + media + ".png"
        event = dict(
            id=str(uuid4()),
            source="manual",
            title="Team invitations",
            text="Review invitations",
            revision=sha,
            changed_paths=["ui/invitations.tsx"],
            source_url="https://example.org/invites",
            edits=[
                dict(
                    path=self.path,
                    before=self.original,
                    after=self.original
                    + "\n\nOpen Invitations.\n\n![Invitations]("
                    + link
                    + ")",
                    reason="Update",
                )
            ],
        )
        item = self.store.ingest("docs", "owner", event)["item_id"]
        self.store.attach_evidence("docs", "owner", item, 1, export)
        self.store.review("docs", "owner", item, 2, "accept_item")
        self.store.review("docs", "owner", item, 3, "ready")
        self.store.approve("docs", "owner", item, 4, True)
        return item, digest, media

    def library_save(self):
        item, export, mid = self.request_with_evidence()
        payload = dict(item=item, version=5, expected_heads={self.path: None})
        r = self.api.post(self.base + "library/save", json=payload)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            self.api.post(self.base + "library/save", json=payload).json(), r.json()
        )
        return item, r.json()["versions"][self.path], mid

    def test_approved_version_pinned_media_owner_review_and_export(self):
        item, digest, mid = self.library_save()
        r = self.api.get(
            self.base + "library/version", params=dict(path=self.path, digest=digest)
        )
        self.assertTrue(r.json()["diff"])
        self.assertEqual(r.json()["media"][0]["step"], 401)
        params = {"path": self.path, "version": digest}
        image = self.api.get(self.base + "library/media/" + mid, params=params)
        self.assertEqual(hashlib.sha256(image.content).hexdigest(), mid)
        self.assertEqual(
            self.api.get(
                self.base + "library/media/" + mid,
                params={**params, "version": "other"},
            ).status_code,
            404,
        )
        writer = self.client("writer")
        self.assertEqual(writer.get(self.base + "library").status_code, 403)
        self.assertEqual(
            writer.get(self.base + "library/media/" + mid, params=params).status_code,
            403,
        )
        payload = dict(
            path=self.path, digest=digest, format="Training lesson", audience="Owners"
        )
        created = self.api.post(self.base + "library/assets", json=payload).json()["id"]
        self.assertEqual(
            self.api.post(self.base + "library/assets", json=payload).json()["id"],
            created,
        )
        url = self.base + "library/assets/" + created
        self.assertEqual(
            self.api.post(url, json=dict(version=1, action="export")).status_code, 409
        )
        self.assertEqual(
            self.api.post(
                url, json=dict(version=1, action="save", body="Text without evidence")
            ).status_code,
            409,
        )
        self.assertEqual(
            self.api.post(url, json=dict(version=1, action="approve")).status_code, 200
        )
        res = self.api.post(url, json=dict(version=2, action="export"))
        self.assertEqual(
            res.status_code, 200, res.text if res.status_code != 200 else ""
        )
        with zipfile.ZipFile(io.BytesIO(res.content)) as z:
            self.assertIn("Open Invitations.", z.read("docs/" + self.path).decode())
            self.assertTrue(
                any(
                    n.startswith("docs/evidence/") and n.endswith(".png")
                    for n in z.namelist()
                )
            )
        edit = {
            **params,
            "image": mid,
            "operation": "redact",
            "box": {"x": 0, "y": 0, "width": 5, "height": 5},
        }
        edit_id = self.api.post(self.base + "media/edits", json=edit).json()["id"]
        result = self.api.get(self.base + "media/edits/" + edit_id)
        with Image.open(io.BytesIO(result.content)) as im:
            self.assertEqual(im.getpixel((1, 1)), (0, 0, 0))
            self.assertEqual(im.getpixel((8, 8)), (255, 0, 0))
        self.assertEqual(
            writer.get(self.base + "media/edits/" + edit_id).status_code, 403
        )
        self.assertEqual(
            self.api.post(
                self.base + "media/edits",
                json={**edit, "box": {"x": 400, "y": 1, "width": 1, "height": 1}},
            ).status_code,
            409,
        )

    def test_media_gap_preserves_heads_and_rejects_unrelated_article(self):
        ident = self.create(proposal=True)
        self.store.review("docs", "owner", ident, 1, "accept_item")
        self.store.review("docs", "owner", ident, 2, "ready")
        self.store.approve("docs", "owner", ident, 3, True)
        r = self.api.post(
            self.base + "library/save",
            json=dict(item=ident, version=4, expected_heads={self.path: None}),
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.api.get(self.base + "library").json()["versions"], [])
        self.assertIsNone(self.item(ident)["delivery"])

    def test_refresh_only_matching_signed_source_and_no_head_mutation(self):
        item, digest, mid = self.library_save()
        with self.pool.connection() as db:
            for p in ("admin/unrelated.py", "ui/invitations.tsx", "ui/invitations.tsx"):
                refresh.record(
                    db,
                    self.org,
                    "docs",
                    dict(revision="b" * 40, changed_paths=[p]),
                    item,
                )
        self.assertTrue(refresh.tick(self.pool))
        data = self.api.get(self.base + "operations").json()["refresh"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], "waiting")
        self.assertEqual(
            self.api.get(self.base + "library").json()["versions"][0]["digest"], digest
        )

    def test_read_grant_scopes_revocation_and_citations(self):
        item = self.create(proposal=True)
        writer = self.client("writer")
        grant = writer.post(self.base + "ask/keys", json={"label": "CLI"}).json()
        headers = {"Authorization": "Bearer " + grant["key"]}
        endpoint = "/api/assistant/search"
        q = {"question": "invitations"}
        self.assertEqual(
            writer.post(endpoint, json=q, headers=headers).json()["results"], []
        )
        self.store.review("docs", "owner", item, 1, "assign", assignee="writer")
        hits = writer.post(endpoint, json=q, headers=headers).json()["results"]
        self.assertEqual(hits[0]["citation"]["item"], item)
        self.assertEqual(
            writer.post(self.base + "writing", json={}, headers=headers).status_code,
            401,
        )
        writer.post(self.base + "ask/keys/" + grant["id"] + "/revoke", json={})
        self.assertEqual(
            writer.post(endpoint, json=q, headers=headers).status_code, 401
        )

    def test_import_conflicts_and_stale_base(self):
        endpoint = self.base + "operations/import-api"
        data = dict(
            path="api/endpoints.md",
            reference="https://example.org/schema",
            spec={
                "openapi": "3.0.3",
                "paths": {"/invite": {"get": {"summary": "List invitations"}}},
            },
        )
        a = self.api.post(endpoint, json=data)
        self.assertEqual(a.status_code, 200, a.text)
        self.assertTrue(self.api.post(endpoint, json=data).json()["duplicate"])
        self.assertEqual(
            self.api.post(
                endpoint, json={**data, "spec": {"openapi": "2.0"}}
            ).status_code,
            409,
        )
        ident = self.create(proposal=True)
        digest = self.store.snapshot("docs", "owner")["articles"][self.path]["digest"]
        article = self.store.article(
            "docs",
            "owner",
            self.path,
            "Team invitations",
            "New upstream.",
            expected=digest,
        )
        payload = dict(
            item_id=ident,
            version=1,
            action="reconcile",
            data=dict(
                path=self.path, change_id="1", base_digest=digest, after="Combined text"
            ),
        )
        self.assertEqual(
            self.api.post(self.base + "review", json=payload).status_code, 409
        )
        payload["data"]["base_digest"] = article["digest"]
        item = self.api.post(self.base + "review", json=payload).json()
        self.assertEqual(item["changes"][0]["before"], "New upstream.")
        self.assertEqual(item["changes"][0]["decision"], "pending")

    def test_reader_redirects_scoped_and_inconclusive_retirement_preserves_head(self):
        item, digest, _ = self.library_save()
        res = self.api.post(
            self.base + "reader/redirects",
            json={"source": "old.md", "target": self.path},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(
            self.api.get(
                self.base + "reader/current", params={"path": "old.md"}
            ).json()["digest"],
            digest,
        )
        self.assertEqual(
            self.api.post(
                self.base + "reader/redirects",
                json={"source": self.path, "target": "old.md"},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client("writer").get(self.base + "reader/llms.txt").status_code, 403
        )
        retirement = {
            "path": self.path,
            "version": digest,
            "item": item,
            "reason": "The control was missing from one session.",
        }
        res = self.api.post(self.base + "reader/retire", json=retirement)
        self.assertEqual(res.json()["status"], "investigate")
        self.assertEqual(res.json()["incoming_links"], ["old.md"])
        self.assertEqual(
            self.api.post(
                self.base + "reader/retire",
                json={**retirement, "confirmed_task_removal": True},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.api.get(
                self.base + "reader/current", params={"path": self.path}
            ).json()["digest"],
            digest,
        )

    def test_publication_requires_separate_merge_build_and_live_bytes(self):
        import hmac
        from cqa_artifacts.hosted.publication import record

        item, version, mid = self.library_save()
        approval = self.item(item)["approval"]["digest"]
        sha = "b" * 40
        from cqa_artifacts.hosted.onboarding import setup

        key = (self.org, "docs", item, approval)
        with self.pool.connection() as db:
            setup(db, self.org, "docs")
            db.execute(
                "UPDATE docs_setup SET connected=true,docs_repo='fake/docs' WHERE organization_id=%s AND project_id='docs'",
                (self.org,),
            )
            db.execute(
                "INSERT INTO docs_guide_prs(organization_id,project_id,item_id,approval_digest,status) VALUES(%s,%s,%s,%s,'merged')",
                key,
            )
            record(db, key, "merge", sha, {"pull_request": "fixture"})
        cfg = {
            "publication_webhook_secret": "fixture-webhook-secret",
            "published_markdown_origin": "https://example.org/docs",
        }
        body = json.dumps(
            dict(
                item=item,
                approval=approval,
                repository="fake/docs",
                commit=sha,
                successful=True,
                build_id="fixture-build",
            )
        ).encode()
        sig = (
            "sha256="
            + hmac.new(
                cfg["publication_webhook_secret"].encode(), body, hashlib.sha256
            ).hexdigest()
        )
        verify = self.base + "publication/" + item + "/verify"
        with patch("cqa_artifacts.hosted.publication.binding", return_value=cfg):
            self.assertEqual(self.api.post(verify, json={}).status_code, 409)
            self.assertEqual(
                self.api.post(
                    self.base + "publication/build", content=body
                ).status_code,
                401,
            )
            self.assertEqual(
                self.api.post(
                    self.base + "publication/build",
                    content=body,
                    headers={"x-docs-signature": sig},
                ).status_code,
                200,
            )
            with patch(
                "cqa_artifacts.hosted.publication.fetch_public",
                side_effect=core.Rejected("Live mismatch"),
            ):
                self.assertEqual(self.api.post(verify, json={}).status_code, 409)
            with patch("cqa_artifacts.hosted.publication.fetch_public") as fetch:
                self.assertEqual(
                    self.api.post(verify, json={}).json()["status"], "live_verified"
                )
                self.assertEqual(fetch.call_count, 2)
        phases = self.api.get(self.base + "operations").json()["phases"]
        self.assertEqual([p["phase"] for p in phases], ["merge", "build", "live"])

    def test_approved_media_quota_rolls_back_all_delivery_writes(self):
        item, _, _ = self.request_with_evidence()
        with patch(
            "cqa_artifacts.hosted.onboarding.binding",
            return_value={"guide_media_quota_bytes": 1},
        ):
            res = self.api.post(
                self.base + "library/save",
                json=dict(item=item, version=5, expected_heads={self.path: None}),
            )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(self.api.get(self.base + "library").json()["versions"], [])
        self.assertIsNone(self.item(item)["delivery"])

    def test_gitbook_root_parser_and_scoped_run_proposal(self):
        from cqa_artifacts.hosted.destinations import configured_root

        self.assertEqual(configured_root("root: ./docs/\n"), "docs")
        with self.assertRaises(core.Rejected):
            configured_root("root: ../client\n")
        source = self.create(proposal=True)
        payload = dict(
            request_id=str(uuid4()), source_item=source, goal="Document invitations"
        )
        a = self.api.post(self.base + "ask/propose", json=payload)
        self.assertEqual(a.status_code, 200, a.text)
        self.assertTrue(
            self.api.post(self.base + "ask/propose", json=payload).json()["duplicate"]
        )
        self.assertEqual(
            self.client("writer")
            .post(self.base + "ask/propose", json=payload)
            .status_code,
            403,
        )
