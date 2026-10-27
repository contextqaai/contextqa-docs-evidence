import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from cqa_artifacts import core

PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic-test-bytes"


class EvidenceBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "private-workspace"
        core.init(self.root, "Synthetic walkthrough")
        self.out = Path(self.temp.name) / "export"

    def tearDown(self):
        self.temp.cleanup()

    def step(self, text="Open the synthetic settings screen"):
        core.add_step(self.root, "Settings", text)

    def approve(self):
        core.approve(self.root, "Synthetic fixture reviewer", True)

    def test_export_requires_explicit_content_review(self):
        self.step()
        with self.assertRaises(core.Rejected):
            core.approve(self.root, "reviewer", False)
        with self.assertRaises(FileNotFoundError):
            core.export(self.root, self.out, "https://docs.example.com/demo")

    def test_no_raw_data_or_unselected_media_in_public_export(self):
        self.step()
        core.write_json(self.root / "private" / "raw.json", {"secret": "PRIVATE_CUSTOMER_VALUE"})
        selected = core.add_media_bytes(self.root, PNG, "screenshot")
        unselected = core.add_media_bytes(self.root, PNG + b"UNSELECTED_PRIVATE_FRAME", "screenshot")
        core.attach(self.root, 1, selected)
        self.approve()
        core.export(self.root, self.out, "https://docs.example.com/demo")
        names = [p.name for p in self.out.rglob("*")]
        self.assertNotIn("raw.json", names)
        self.assertFalse(any(unselected in name for name in names))
        self.assertEqual(len(list((self.out / "assets").iterdir())), 1)

    def test_text_is_redacted_and_not_active_html_or_markdown(self):
        self.step('<script>alert(1)</script> token_demo.secret123 jane@example.com https://secret.example/?key=x [click](javascript:alert(1))')
        self.approve()
        core.export(self.root, self.out, "https://docs.example.com/demo")
        for name in ["index.html", "guide.md", "manifest.json"]:
            text = (self.out / name).read_text()
            self.assertNotIn("token_demo.secret123", text)
            self.assertNotIn("jane@example.com", text)
            self.assertNotIn("secret.example", text)
        self.assertNotIn("<script>", (self.out / "index.html").read_text())
        self.assertNotIn("<script>", (self.out / "guide.md").read_text())
        self.assertNotIn("[click](javascript:", (self.out / "guide.md").read_text())

    def test_changed_steps_and_media_invalidate_review(self):
        self.step()
        mid = core.add_media_bytes(self.root, PNG, "screenshot")
        core.attach(self.root, 1, mid)
        self.approve()
        core.edit_step(self.root, 1, "Changed", "Different workflow")
        with self.assertRaises(core.Rejected):
            core.export(self.root, self.out, "https://docs.example.com/demo")
        self.approve()
        asset = next((self.root / "assets").iterdir())
        asset.write_bytes(PNG + b"Changed pixels")
        with self.assertRaises(core.Rejected):
            core.export(self.root, self.out, "https://docs.example.com/demo")

    def test_source_html_and_svg_cannot_be_media(self):
        for payload in [b'<svg onload="alert(1)"></svg>', b'<html><script>fetch("secret")</script></html>']:
            with self.assertRaises(core.Rejected):
                core.add_media_bytes(self.root, payload, "screenshot")

    def test_symlink_asset_directory_is_rejected(self):
        assets = self.root / "assets"
        assets.rmdir()
        assets.symlink_to(Path(self.temp.name), target_is_directory=True)
        with self.assertRaises(core.Rejected):
            core.add_media_bytes(self.root, PNG, "screenshot")

    def archive(self, name, payload=b"", mode=None):
        target = Path(self.temp.name) / "trace.zip"
        with zipfile.ZipFile(target, "w") as z:
            info = zipfile.ZipInfo(name)
            if mode:
                info.external_attr = mode << 16
            z.writestr(info, payload)
        return target

    def test_archive_traversal_and_symlink_rejected_before_import(self):
        for name, mode in [("../../escape.trace", None), ("/absolute.trace", None), ("resources/link", stat.S_IFLNK | 0o777)]:
            path = self.archive(name, b"outside", mode)
            with self.assertRaises(core.Rejected):
                core.import_trace(self.root, path)
        self.assertEqual(core.manifest(self.root)["steps"], [])

    def test_trace_import_has_no_dom_network_or_video_export(self):
        path = Path(self.temp.name) / "trace.zip"
        events = [
            {"type": "before", "method": "fill", "params": {"value": "PRIVATE_PASSWORD"}},
            {"type": "screencast-frame", "sha1": "frame.jpeg"},
        ]
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("0.trace", "\n".join(json.dumps(e) for e in events))
            z.writestr("0.network", '{"Authorization":"PRIVATE_BEARER"}')
            z.writestr("0.snapshot", '<html>PRIVATE_DOM</html>')
            z.writestr("resources/frame.jpeg", b"\xff\xd8\xffsynthetic-image")
        result = core.import_trace(self.root, path)
        self.assertFalse(result["video_created"])
        self.assertFalse(result["dom_exported"])
        self.assertNotIn("PRIVATE_PASSWORD", (self.root / "manifest.json").read_text())
        with self.assertRaises(core.Rejected):
            self.approve()
        core.edit_step(self.root, 1, "Enter demo information", "Use the approved synthetic record")
        self.approve()
        core.export(self.root, self.out, "https://docs.example.com/demo")
        self.assertFalse(list(self.out.rglob("*.zip")))
        self.assertFalse(list(self.out.rglob("*.network")))

    def test_paid_execution_and_arbitrary_http_paths_are_not_callable(self):
        with patch("urllib.request.build_opener") as opener:
            for path in ["/test_plans/1/execution", "https://attacker.example/", "/api/tokens", "/test_plan_results/1/results?token=secret"]:
                with self.assertRaises(core.Rejected):
                    core.api_read("secret-token", path)
            opener.assert_not_called()

    def test_redirects_cannot_forward_credentials(self):
        with self.assertRaises(core.Rejected):
            core.NoRedirect().redirect_request(None, None, None, None, None, "https://attacker.example")

    def test_cross_run_result_cannot_be_attached(self):
        with patch.object(core, "api_read", side_effect=[{"status": "STATUS_COMPLETED"}, {"testPlanResultId": 999}]):
            with self.assertRaises(core.Rejected):
                core.collect(self.root, "test-secret", 1, [2], [])
        self.assertFalse((self.root / "private" / "contextqa-results.json").exists())

    def test_result_collection_keeps_signed_references_private(self):
        summary = {"status": "STATUS_IN_PROGRESS", "result": "IN_PROGRESS", "reportFileUrl": "https://assets.example/report?signature=SECRET"}
        with patch.object(core, "api_read", return_value=summary):
            receipt = core.collect(self.root, "test-secret", 1, [], [])
        self.assertEqual(receipt["result"], "IN_PROGRESS")
        self.assertNotIn("SECRET", json.dumps(receipt))
        self.assertFalse(receipt["paid_execution_started"])
        self.assertEqual(receipt["artifact_references"], 1)

    def test_export_cannot_overwrite_an_existing_or_private_directory(self):
        self.step()
        self.approve()
        with self.assertRaises(core.Rejected):
            core.export(self.root, self.root, "https://docs.example.com/demo")
        self.assertTrue((self.root / "private").exists())


if __name__ == "__main__":
    unittest.main()
