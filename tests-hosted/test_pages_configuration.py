import unittest
from cqa_artifacts.core import Rejected
from cqa_artifacts.hosted.destinations import pages_configuration


class PagesConfigurationTests(unittest.TestCase):
    cfg = dict(docs_repo="example/guide", branch="release", docs_root="docs")
    site = dict(html_url="https://example.github.io/guide/", public=True,
                build_type="legacy", source={"branch": "release", "path": "/docs"})

    def test_selected_branch_and_folder(self):
        receipt = pages_configuration(self.cfg, self.site)
        self.assertEqual(receipt["status"], "configuration_verified")
        self.assertFalse(receipt["public_site_verified"])

    def test_ineligible_destinations(self):
        for changes in (dict(public=False), dict(public=None), dict(build_type="workflow"),
                        dict(source={"branch": "main", "path": "/docs"}),
                        dict(source={"branch": "release", "path": "/"}),
                        dict(html_url="http://sample.invalid/")):
            with self.subTest(changes=changes), self.assertRaises(Rejected):
                pages_configuration(self.cfg, self.site | changes)
