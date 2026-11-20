import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from cqa_artifacts import core
from cqa_artifacts.loop import Store

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('sim_demo',ROOT/'examples/contextqa_demo.py')
demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        demo.main(self.root/'simulation')
        self.export=self.root/'simulation/guide'
        self.store=Store(self.root/'db')
        self.manifest=json.loads((ROOT/'examples/docs-loop/manifest.json').read_text())
        self.manifest['allow_simulated_evidence']=True
        self.store.create(self.manifest)
        self.event=dict(id='capture',source='manual',title='Capture',text='Synthetic capture intake',requires_capture=True,
            edits=[dict(path='guides/projects.md',before='',after='Synthetic instructions',reason='Fixture')])
        self.item=self.store.ingest('demo','owner',self.event)['item_id']
    def test_simulated_evidence_labeled_and_packaged(self):
        i=self.store.attach_evidence('demo','owner',self.item,1,self.export)
        i=self.store.review('demo','owner',self.item,i['version'],'answer',text='Synthetic validation only')
        i=self.store.review('demo','owner',self.item,i['version'],'accept',change_id='1')
        i=self.store.review('demo','owner',self.item,i['version'],'ready')
        self.store.approve('demo','owner',self.item,i['version'],True)
        bundle=self.store.bundle('demo','owner',self.item)
        self.assertEqual(bundle['evidence'][0]['execution']['transport'],'simulated')
        self.assertTrue(any(p.endswith('/index.html') for p in bundle['evidence_files']))
        self.assertNotIn('SIMULATED_PRIVATE',json.dumps(bundle))
    def test_simulated_disabled_by_default(self):
        with self.store.transaction('demo') as s:del s['manifest']['allow_simulated_evidence']
        with self.assertRaises(core.Rejected):self.store.attach_evidence('demo','owner',self.item,1,self.export)
    def test_missing_screenshot_rejected(self):
        with self.store.transaction('demo') as s:s['events']['capture']['event']['requires_screenshots']=True
        with self.assertRaises(core.Rejected):self.store.attach_evidence('demo','owner',self.item,1,self.export)
    def test_failed_capture_cannot_satisfy_requirement(self):
        p=self.export/'manifest.json';d=json.loads(p.read_text());d['execution']['verdict']='failed';p.write_text(json.dumps(d))
        (self.export/'review-receipt.json').write_text(json.dumps(dict(digest=core.export_digest(d),rights_and_media_review_confirmed=True)))
        with self.assertRaises(core.Rejected):self.store.attach_evidence('demo','owner',self.item,1,self.export)
    def test_evidence_tampering_rejected(self):
        self.store.attach_evidence('demo','owner',self.item,1,self.export)
        p=self.export/'manifest.json';d=json.loads(p.read_text());d['steps'][0]['instruction']='Changed';p.write_text(json.dumps(d))
        with self.assertRaises(core.Rejected):self.store.attach_evidence('demo','owner',self.item,2,self.export)
    def test_wrong_version_rejected(self):
        with self.store.transaction('demo') as s:s['events']['capture']['event']['revision']='expected-sha'
        with self.assertRaises(core.Rejected):self.store.attach_evidence('demo','owner',self.item,1,self.export)
