import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from cqa_artifacts import guides
from cqa_artifacts.core import Rejected

FIXTURE=Path(__file__).resolve().parent/'fixtures/editorial-guide.json'

class EditorialGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.example=Path(self.temp.name)
        self.spec=json.loads(FIXTURE.read_text())
        raw=b'\x89PNG\r\n\x1a\nexplicit-synthetic-renderer-fixture'
        for figure in self.spec['figures']:
            target=self.example/figure['path'];target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
            figure['sha256']=hashlib.sha256(raw).hexdigest()
        (self.example/'guide-spec.json').write_text(json.dumps(self.spec))
    def compiled(self,spec=None):
        return guides.compile_guide(spec or self.spec,self.example)
    def test_synthetic_layout_keeps_execution_gap(self):
        output=self.compiled()
        self.assertEqual(len(output['assets']),7)
        self.assertEqual(output['html'].count('<figure>'),7)
        self.assertFalse(output['report']['publication_ready'])
        self.assertTrue(any('execution missing' in b for b in output['report']['blockers']))
        self.assertIn('Check your progress',output['markdown'])
    def test_unchanged_guide_is_deterministic(self):
        a=self.compiled();b=self.compiled()
        self.assertEqual(a,b)
        self.assertTrue(guides.impact(a['report'],b['report'])['no_change'])
    def test_figure_change_marks_only_dependent_section(self):
        before=self.compiled()['report']
        self.spec['figures'][0]['caption']='A reviewed replacement caption.'
        delta=guides.impact(before,self.compiled()['report'])
        self.assertEqual([r['section'] for r in delta['changed_sections']],['name-the-plan'])
        self.assertIn('figure_digests',delta['changed_sections'][0]['reasons'])
    def test_prerequisite_and_order_changes_are_not_noops(self):
        before=self.compiled()['report']
        self.spec['prerequisites'].append('A new prerequisite.')
        self.assertTrue(guides.impact(before,self.compiled()['report'])['document_changed'])
        self.spec['sections'].reverse()
        self.assertTrue(guides.impact(before,self.compiled()['report'])['section_order_changed'])
    def test_tampered_image_blocks_build(self):
        self.spec['figures'][0]['sha256']='0'*64
        with self.assertRaises(Rejected):self.compiled()
    def test_traversal_and_cross_source_image_rejected(self):
        self.spec['figures'][0]['path']='../../../../README.md'
        with self.assertRaises(Rejected):self.compiled()
        self.setUp();self.spec['sections'][1]['source_ids']=['learning-hub']
        with self.assertRaises(Rejected):self.compiled()
    def test_unknown_reference_and_duplicate_ids_rejected(self):
        self.spec['sections'][1]['figure_ids']=['unknown']
        with self.assertRaises(Rejected):self.compiled()
        self.setUp();self.spec['figures'].append(copy.deepcopy(self.spec['figures'][0]))
        with self.assertRaises(Rejected):self.compiled()
    def test_failed_execution_cannot_satisfy_gate(self):
        source=dict(id='failed-run',kind='contextqa-run',url='https://example.com/run',observed_at='2026-11-20',summary='Synthetic negative test',run_id=1,verdict='failed',deployment_verified=True)
        self.spec['sources'].append(source)
        self.spec['sections'][6]['source_ids'].append('failed-run')
        blockers=self.compiled()['report']['blockers']
        self.assertIn('Unverified or failed execution: failed-run',blockers)
        self.assertTrue(any(b.startswith('run-and-monitor:') for b in blockers))
    def test_html_text_is_escaped(self):
        self.spec['summary']='<script>alert(1)</script>'
        self.assertNotIn('<script>',self.compiled()['html'])
        self.assertNotIn('<script>',self.compiled()['markdown'])
    def test_build_rejects_browser_capture_benchmark(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'guide'
            with self.assertRaisesRegex(Rejected,'ContextQA-only'):
                guides.build(self.example/'guide-spec.json',self.example,out)
            self.assertFalse(out.exists())
    def test_changing_product_reference_fans_out_to_dependent_sections(self):
        before=self.compiled()['report'];self.spec['sources'][2]['summary']='Changed API configuration'
        delta=guides.impact(before,self.compiled()['report'])
        self.assertEqual({r['section'] for r in delta['changed_sections']},{'understand-the-plan','verify-saved-plan'})

if __name__=='__main__':unittest.main()
