import base64
import json
import unittest
from unittest.mock import patch

from cqa_artifacts.core import Rejected
from cqa_artifacts.hosted.destinations import verify_pages_release


class PagesReleaseTests(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(branch="publish", docs_repo="Org/Docs", docs_root="docs")
        self.revision = "1" * 40
        self.files = {"index.html": "2" * 64, "images/a.jpg": "3" * 64}
        self.build = {"commit": self.revision, "status": "built", "url": "receipt"}
        self.source = dict(public=True, build_type="legacy", html_url="https://org.github.io/Docs/",
                           source={"branch": "publish", "path": "/docs"})

    def provider(self, config, path, params=None):
        if path.endswith("/pages"):
            return self.source
        if path.endswith("/commits/publish"):
            return {"sha": self.revision}
        if path.endswith("/latest"):
            return self.build
        self.assertEqual((path, params), ("/repos/Org/Docs/contents/docs/release.json", {"ref": self.revision}))
        raw = json.dumps({"files": self.files}).encode()
        return {"type": "file", "encoding": "base64", "content": base64.b64encode(raw).decode()}

    def test_only_matching_public_bytes_earn_a_receipt(self):
        with patch("cqa_artifacts.hosted.destinations.github_get", self.provider), patch("cqa_artifacts.hosted.destinations.fetch_public") as read:
            receipt = verify_pages_release({}, self.cfg)
            self.assertEqual(receipt["revision"], self.revision)
            self.assertEqual(read.call_count, 3)
            read.assert_any_call("https://org.github.io/Docs/images/a.jpg", "3" * 64)
            read.side_effect = Rejected("Missing figure")
            with self.assertRaises(Rejected):
                verify_pages_release({}, self.cfg)

    def test_wrong_build_or_unsafe_manifest_prevents_any_reader_request(self):
        with patch("cqa_artifacts.hosted.destinations.github_get", self.provider), patch("cqa_artifacts.hosted.destinations.fetch_public") as read:
            self.build["status"] = "building"
            with self.assertRaises(Rejected):
                verify_pages_release({}, self.cfg)
            self.build["status"] = "built"
            self.files["../private"] = "4" * 64
            with self.assertRaises(Rejected):
                verify_pages_release({}, self.cfg)
            read.assert_not_called()
