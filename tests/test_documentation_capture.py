from pathlib import Path
import tempfile
import unittest
from cqa_artifacts import core
from cqa_artifacts.changes import compare

class DocumentationCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.w = self.root / 'workspace'
        core.init(self.w, 'Create a card')
        core.add_step(self.w, 'Open the form', 'Choose Add card.')
        self.mid = core.add_media_bytes(self.w, b'\x89PNG\r\n\x1a\nsynthetic-unit-test-only', 'screenshot')
        core.attach(self.w, 1, self.mid)
        self.box = dict(media_id=self.mid, x=10, y=20, width=30, height=10, label='Choose Add card')

    def test_annotations_are_exported_and_escape_html(self):
        self.box['label'] = '<script>alert(1)</script>'
        core.annotate(self.w, 1, [self.box])
        core.approve(self.w, 'test', True)
        core.export(self.w, self.root/'export', 'https://example.com/docs')
        page = (self.root/'export/index.html').read_text()
        self.assertIn('left:10%;top:20%;width:30%;height:10%', page)
        self.assertNotIn('<script>', page)
        self.assertIn('View annotated screenshots', (self.root/'export/guide.md').read_text())

    def test_annotation_change_invalidates_review(self):
        core.approve(self.w, 'test', True)
        core.annotate(self.w, 1, [self.box])
        with self.assertRaises(core.Rejected):
            core.export(self.w, self.root/'export', 'https://example.com/docs')

    def test_invalid_boxes_rejected_without_mutation(self):
        before = core.manifest(self.w)
        for override in [{'x': float('nan')}, {'x': True}, {'width': 0}, {'x':99}, {'media_id':'missing'}, {'label':''}]:
            with self.subTest(override=override), self.assertRaises(core.Rejected):
                core.annotate(self.w, 1, [dict(self.box, **override)])
        self.assertEqual(before, core.manifest(self.w))

    def test_capture_labels_are_review_bound_not_execution_claims(self):
        core.approve(self.w, 'test', True)
        core.set_context(self.w, {'workflow_id':'kan-create-card', 'captured_at':'2026-10-31T04:00:00Z', 'app_version':'main', 'runner_mode':'unverified'})
        with self.assertRaises(core.Rejected):
            core.export(self.w, self.root/'export', 'https://example.com/docs')
        core.approve(self.w, 'test', True)
        core.export(self.w, self.root/'export', 'https://example.com/docs')
        self.assertIn('operator supplied', (self.root/'export/index.html').read_text())
        self.assertNotIn('execution', core.clean_export(self.w))

    def test_invalid_capture_metadata_rejected(self):
        for value in [{'password':'private'}, {'captured_at':'today'}, {'captured_at':'2026-10-31T04:00:00'}, {'commit_sha':'main'}]:
            with self.assertRaises(core.Rejected):core.set_context(self.w, value)

    def test_run_ids_do_not_make_false_documentation_changes(self):
        import json
        for label, rid in [('old',11),('new',22)]:
            d = core.manifest(self.w)
            d['steps'][0].update(case_result_id=rid, step_result_id=rid)
            core.save(self.w,d)
            core.approve(self.w,'test',True)
            core.export(self.w,self.root/label,'https://example.com/docs')
        info = dict(before_version='a',after_version='b',what_changed='Recapture',affected_documents='Cards',step_pairs=[dict(before=1,after=1)])
        (self.root/'context.json').write_text(json.dumps(info))
        report=compare(self.root/'old',self.root/'new',self.root/'context.json',self.root/'comparison')
        self.assertEqual(report['changed'],0)
