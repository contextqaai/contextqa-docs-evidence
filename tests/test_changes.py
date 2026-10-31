import json
from pathlib import Path
import tempfile
import unittest
from cqa_artifacts import core
from cqa_artifacts.changes import compare


class ChangesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for label, instruction in [('old', 'Select Projects.'), ('new', 'Select Workspace.')]:
            w = self.root / (label + '-workspace')
            core.init(w, 'Synthetic guide')
            core.add_step(w, 'Navigation', instruction)
            core.approve(w, 'Reviewer', True)
            core.export(w, self.root / label, 'https://docs.example.com/demo')
        self.info = {'before_version': 'a', 'after_version': 'b', 'what_changed': 'Navigation renamed', 'affected_documents': 'Onboarding', 'step_pairs': [{'before': 1, 'after': 1}]}
        self.context = self.root / 'context.json'

    def run_compare(self):
        self.context.write_text(json.dumps(self.info))
        return compare(self.root / 'old', self.root / 'new', self.context, self.root / 'result')

    def test_explicit_change_and_context(self):
        self.assertEqual(self.run_compare()['changed'], 1)
        self.assertIn('Select Workspace', (self.root / 'result/refresh-draft.md').read_text())
        self.assertEqual(sorted(p.name for p in (self.root / 'result').iterdir()), ['assets', 'changes.json', 'index.html', 'refresh-draft.md'])

    def test_changed_export_rejected(self):
        p = self.root / 'new/manifest.json'
        data = json.loads(p.read_text())
        data['steps'][0]['instruction'] = 'Unreviewed change'
        p.write_text(json.dumps(data))
        with self.assertRaises(core.Rejected):
            self.run_compare()

    def test_missing_or_incomplete_mapping_rejected(self):
        self.info['step_pairs'] = [{'before': 1, 'after': None}]
        with self.assertRaises(core.Rejected):
            self.run_compare()

    def test_add_remove_and_untrusted_context(self):
        self.info['step_pairs'] = [{'before': 1, 'after': None}, {'before': None, 'after': 1}]
        self.info['what_changed'] = '<script>alert(1)</script> token_demo.ABCDEF123456'
        self.assertEqual(self.run_compare()['changed'], 2)
        draft = (self.root / 'result/refresh-draft.md').read_text()
        self.assertNotIn('<script>', draft)
        self.assertNotIn('ABCDEF123456', draft)

    def test_missing_review_receipt_rejected(self):
        (self.root / 'new/review-receipt.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_compare()

    def test_only_reviewed_attached_media_are_copied(self):
        w = self.root / 'new-workspace'
        selected = core.add_media_bytes(w, b'\x89PNG\r\n\x1a\nsynthetic-frame', 'screenshot')
        core.add_media_bytes(w, b'\x89PNG\r\n\x1a\nprivate-unused-frame', 'screenshot')
        core.attach(w, 1, selected)
        core.approve(w, 'Reviewer', True)
        core.export(w, self.root / 'with-media', 'https://docs.example.com/demo')
        (self.root / 'with-media/private-extra.txt').write_text('MUST_NOT_COPY')
        self.context.write_text(json.dumps(self.info))
        compare(self.root / 'old', self.root / 'with-media', self.context, self.root / 'result')
        self.assertEqual(len(list((self.root / 'result/assets').glob('*.png'))), 1)
        self.assertTrue((self.root / 'result/assets/contextqa-logo.svg').exists())
        self.assertFalse((self.root / 'result/private-extra.txt').exists())
        self.assertIn(selected, (self.root / 'result/index.html').read_text())

    def test_duplicate_step_pair_rejected(self):
        self.info['step_pairs'] *= 2
        with self.assertRaises(core.Rejected):
            self.run_compare()
