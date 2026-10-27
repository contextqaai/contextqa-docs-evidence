"""Exercise the reviewed-export boundary before optional AI data sharing."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest

from cqa_artifacts import core


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare-ai-input.py"
SPEC = importlib.util.spec_from_file_location("prepare_ai_input", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrepareAIInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.export = self.root / "reviewed-export"
        self.destination = self.root / "ai-input.json"
        core.init(self.workspace, "Reviewed synthetic guide")
        core.add_step(self.workspace, "Open Projects", "Select Projects in the navigation.")
        core.add_step(self.workspace, "Create a draft", "Enter the approved synthetic title.")
        self.media_id = core.add_media_bytes(
            self.workspace, b"\x89PNG\r\n\x1a\nPRIVATE_SCREENSHOT_BYTES", "screenshot"
        )
        core.attach(self.workspace, 1, self.media_id)
        core.approve(self.workspace, "Synthetic fixture reviewer", True)
        core.export(self.workspace, self.export, "https://docs.example.com/demo")

    def prepare(self, source=None):
        return MODULE.prepare(source or self.export, self.destination)

    def change_json(self, path, transform):
        data = json.loads(path.read_text())
        transform(data)
        path.write_text(json.dumps(data))

    def test_verified_export_yields_only_reviewed_title_and_step_text(self):
        expected = {
            "title": "Reviewed synthetic guide",
            "steps": [
                {"title": "Open Projects", "instruction": "Select Projects in the navigation."},
                {"title": "Create a draft", "instruction": "Enter the approved synthetic title."},
            ],
        }
        self.assertEqual(self.prepare(), expected)
        self.assertEqual(json.loads(self.destination.read_text()), expected)
        self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o600)

    def test_media_private_fields_and_unrelated_files_never_enter_payload(self):
        def add_private_metadata(data):
            data["private"] = {"authorization": "PRIVATE_ROOT_FIELD"}
            data["source"] = "PRIVATE_SOURCE_REFERENCE"
            data["steps"][0]["private"] = "PRIVATE_STEP_FIELD"
            data["media"][0]["private"] = "PRIVATE_MEDIA_FIELD"

        self.change_json(self.export / "manifest.json", add_private_metadata)
        private = self.export / "private"
        private.mkdir()
        (private / "raw-trace.json").write_text("PRIVATE_RAW_TRACE")
        (self.export / "extra.html").write_text("PRIVATE_HTML_DOCUMENT")
        self.prepare()
        text = self.destination.read_text()
        self.assertNotIn("PRIVATE_", text)
        self.assertNotIn(self.media_id, text)
        self.assertNotIn("assets/", text)
        self.assertNotIn("media", json.loads(text))
        self.assertEqual(set(json.loads(text)), {"title", "steps"})
        for step in json.loads(text)["steps"]:
            self.assertEqual(set(step), {"title", "instruction"})

    def test_private_workspace_approval_is_not_an_export_receipt(self):
        with self.assertRaises(FileNotFoundError):
            self.prepare(self.workspace)
        self.assertFalse(self.destination.exists())

    def test_missing_review_receipt_does_not_create_output(self):
        (self.export / "review-receipt.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_missing_rights_and_media_confirmation_does_not_create_output(self):
        self.change_json(
            self.export / "review-receipt.json",
            lambda data: data.update(rights_and_media_review_confirmed=False),
        )
        with self.assertRaises(core.Rejected):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_modified_reviewed_instruction_invalidates_receipt(self):
        self.change_json(
            self.export / "manifest.json",
            lambda data: data["steps"][0].update(instruction="Unreviewed replacement instruction"),
        )
        with self.assertRaises(core.Rejected):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_wrong_receipt_digest_does_not_create_output(self):
        self.change_json(
            self.export / "review-receipt.json", lambda data: data.update(digest="0" * 64)
        )
        with self.assertRaises(core.Rejected):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_modified_attached_media_invalidates_export_even_when_text_is_unchanged(self):
        asset = next((self.export / "assets").iterdir())
        asset.write_bytes(b"\x89PNG\r\n\x1a\nUNREVIEWED_SCREENSHOT")
        with self.assertRaises(core.Rejected):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_output_cannot_overwrite_existing_data(self):
        self.destination.write_text("Existing user draft")
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(self.destination.read_text(), "Existing user draft")

    def test_output_symlink_cannot_overwrite_its_target(self):
        target = self.root / "keep.txt"
        target.write_text("Keep this user file")
        self.destination.symlink_to(target)
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(target.read_text(), "Keep this user file")


if __name__ == "__main__":
    unittest.main()
