"""Supported screenshot references remain bounded to known trace layouts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from cqa_artifacts import core


JPEG_A = b"\xff\xd8\xffsynthetic-frame-a"
JPEG_B = b"\xff\xd8\xffsynthetic-frame-b"
FRAME_FILE = "screencast/page@0123456789abcdef-1793143892110.jpeg"


class TraceFrameFormats(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.trace = Path(self.temp.name) / "trace.zip"
        core.init(self.root, "Synthetic trace")

    def archive(self, events, members):
        with zipfile.ZipFile(self.trace, "w") as archive:
            archive.writestr("trace.trace", "\n".join(json.dumps(event) for event in events))
            for name, payload in members.items():
                archive.writestr(name, payload)

    def test_legacy_sha1_resource_frame_is_imported(self):
        self.archive(
            [{"type": "screencast-frame", "sha1": "frame.jpeg"}],
            {"resources/frame.jpeg": JPEG_A},
        )
        result = core.import_trace(self.root, self.trace)
        self.assertEqual(result["frame_events"], 1)
        media = core.manifest(self.root)["media"]
        self.assertEqual(len(media), 1)
        self.assertEqual((self.root / media[0]["path"]).read_bytes(), JPEG_A)

    def test_explicit_screencast_file_frame_is_imported(self):
        self.archive(
            [{"type": "screencast-frame", "file": FRAME_FILE, "width": 1280, "height": 800}],
            {FRAME_FILE: JPEG_A},
        )
        result = core.import_trace(self.root, self.trace)
        self.assertEqual(result["frame_events"], 1)
        media = core.manifest(self.root)["media"]
        self.assertEqual(len(media), 1)
        self.assertEqual((self.root / media[0]["path"]).read_bytes(), JPEG_A)
        self.assertFalse(result["video_created"])
        self.assertFalse(result["dom_exported"])

    def test_both_formats_and_repeated_frames_preserve_review_boundary(self):
        self.archive(
            [
                {"type": "before", "method": "click", "params": {"value": "PRIVATE_INPUT"}},
                {"type": "screencast-frame", "sha1": "legacy.jpeg"},
                {"type": "screencast-frame", "file": FRAME_FILE},
                {"type": "screencast-frame", "file": FRAME_FILE},
            ],
            {"resources/legacy.jpeg": JPEG_A, FRAME_FILE: JPEG_B},
        )
        result = core.import_trace(self.root, self.trace)
        data = core.manifest(self.root)
        self.assertEqual(result["captured_actions"], 1)
        self.assertEqual(result["frame_events"], 3)
        self.assertEqual(len(data["media"]), 2)
        self.assertTrue(data["steps"][0]["needs_review"])
        self.assertEqual(data["steps"][0]["media"], [])
        self.assertNotIn("PRIVATE_INPUT", json.dumps(data))
        with self.assertRaises(core.Rejected):
            core.approve(self.root, "Reviewer", True)

    def test_invalid_file_reference_is_rejected_before_any_target_member_read(self):
        invalid = [
            "resources/private.jpeg",
            "../resources/private.jpeg",
            "/resources/private.jpeg",
            "screencast/../resources/private.jpeg",
            "screencast/nested/frame.jpeg",
            "screencast\\frame.jpeg",
            "https://example.com/frame.jpeg",
            "screencast/frame.network",
            None,
            [FRAME_FILE],
        ]
        for reference in invalid:
            with self.subTest(reference=reference):
                self.archive(
                    [
                        {"type": "before", "method": "click"},
                        # An otherwise-valid legacy reference cannot override
                        # an invalid explicit file reference.
                        {"type": "screencast-frame", "file": reference, "sha1": "private.jpeg"},
                    ],
                    {"resources/private.jpeg": JPEG_A, FRAME_FILE: JPEG_B},
                )
                original_read = zipfile.ZipFile.read
                read_names = []

                def record_read(archive, name, *args, **kwargs):
                    read_names.append(name.filename if isinstance(name, zipfile.ZipInfo) else name)
                    return original_read(archive, name, *args, **kwargs)

                with patch.object(zipfile.ZipFile, "read", autospec=True, side_effect=record_read):
                    with self.assertRaises(core.Rejected):
                        core.import_trace(self.root, self.trace)
                self.assertEqual(read_names, ["trace.trace"])
                self.assertEqual(core.manifest(self.root)["steps"], [])
                self.assertEqual(core.manifest(self.root)["media"], [])
                self.assertFalse((self.root / "private" / "source-trace.zip").exists())

    def test_missing_screencast_member_is_not_replaced_with_another_image(self):
        self.archive(
            [{"type": "screencast-frame", "file": FRAME_FILE}],
            {"resources/private.jpeg": JPEG_A},
        )
        result = core.import_trace(self.root, self.trace)
        self.assertEqual(result["frame_events"], 0)
        self.assertEqual(core.manifest(self.root)["media"], [])


if __name__ == "__main__":
    unittest.main()
