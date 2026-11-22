"""Synthetic transport checks; not live documentation acceptance."""
import copy
import unittest
from unittest.mock import patch
from test_journeys import JourneyTests
from cqa_artifacts import writer, core, journeys as j
from cqa_artifacts.contextqa import replace_private_json
from cqa_artifacts.loop import fingerprint

class WriterTests(unittest.TestCase):
    setUp=JourneyTests.setUp
    attestation=JourneyTests.attestation
    captured=JourneyTests.captured
    exported=JourneyTests.exported
    editorial_fixture=JourneyTests.editorial_fixture
    # Reuse the isolated repository/client fixture without inheriting its tests.
    def workspace(self):
        export,enriched,specs=self.editorial_fixture()
        specs['guide.md']['review']['independent_task_completion']=True
        out=self.root/'workflow'
        inputs=dict(plan=self.plan,registry=self.registry,runs={'create-card':{'run_id':30}},hosts=['media.example'],max_media=50)
        replace_private_json(out/'inputs.json',inputs)
        replace_private_json(out/'state.json',dict(schema=1,input_digest=fingerprint(inputs),phase='awaiting_editorial_review'))
        import shutil
        shutil.copytree(export,out/'reviewed/create-card')
        recipe=core.load_json(self.root/'capture/private/review-recipe.json') if (self.root/'capture/private/review-recipe.json').exists() else {'steps':[]}
        return out,{'create-card':recipe},specs
    def test_writer_requires_explicit_review(self):
        out,recipes,specs=self.workspace()
        with self.assertRaisesRegex(core.Rejected,'Explicit review'):
            writer.finalize(out,recipes,specs,'Reviewer',self.root/'library',None)
        self.assertFalse((self.root/'library/latest.json').exists())
    def test_writer_finalizes_and_replays_without_duplicate_version(self):
        out,recipes,specs=self.workspace();lib=self.root/'library'
        result=writer.finalize(out,recipes,specs,'Reviewer',lib,None,True,allow_simulated=True)
        self.assertTrue(result['updated'])
        self.assertEqual(writer.finalize(out,recipes,specs,'Reviewer',lib,None,True,allow_simulated=True),result)
        self.assertEqual(len(list((lib/'versions').iterdir())),1)
        specs['guide.md']['summary']='Changed content'
        with self.assertRaisesRegex(core.Rejected,'immutable'):
            writer.finalize(out,recipes,specs,'Reviewer',lib,None,True,allow_simulated=True)
    def test_editorial_blocker_can_be_fixed_without_recapture(self):
        out,recipes,specs=self.workspace();lib=self.root/'library'
        specs['guide.md']['review']['independent_task_completion']=False
        with self.assertRaisesRegex(core.Rejected,'Editorial gates'):
            writer.finalize(out,recipes,specs,'Reviewer',lib,None,True,allow_simulated=True)
        self.assertFalse((lib/'latest.json').exists())
        specs['guide.md']['review']['independent_task_completion']=True
        writer.finalize(out,recipes,specs,'Reviewer',lib,None,True,allow_simulated=True)
    def test_static_preview_escapes_html_and_rejects_script_links(self):
        from cqa_artifacts.library import render_document
        page=render_document('# Guide\n<script>alert(1)</script>\n[bad](javascript:alert)\n![State](../../evidence/image.png)')
        self.assertNotIn('<script>',page)
        self.assertNotIn('href="javascript:',page)
        self.assertIn('src="../../evidence/image.png"',page)
        self.assertIn('&lt;script&gt;',page)
    def test_unchanged_refresh_keeps_verified_library(self):
        out,recipes,specs=self.workspace();lib=self.root/'library'
        first=writer.finalize(out,recipes,specs,'Reviewer',lib,None,True,allow_simulated=True)
        import shutil
        second=self.root/'refresh';shutil.copytree(out,second)
        inputs=core.load_json(second/'inputs.json')
        version=core.load_json(lib/'versions'/first['version']/'version.json')
        planned=inputs['plan'];planned.pop('plan_digest')
        for article in planned['articles']:
            article['before']=version['documents'][article['path']]
            article['base_digest']=fingerprint(article['before'])
        inputs['plan']=j.sealed(planned,'plan_digest')
        replace_private_json(second/'inputs.json',inputs)
        replace_private_json(second/'state.json',dict(input_digest=fingerprint(inputs),phase='awaiting_editorial_review'))
        result=writer.finalize(second,recipes,specs,'Reviewer',lib,first['version'],True,allow_simulated=True)
        self.assertFalse(result['updated'])
        self.assertEqual(result['version'],first['version'])
        self.assertEqual(len(list((lib/'versions').iterdir())),1)
    def test_inflight_collection_can_resume_without_freezing_partial_evidence(self):
        self.client.run.update(status='STATUS_IN_PROGRESS',result='QUEUED')
        out=self.root/'pending'
        with self.assertRaisesRegex(core.Rejected,'not complete'):
            writer.collect(self.client,self.plan,self.registry,{'create-card':{'run_id':30,'deployment':self.attestation()}},out,['media.example'])
        self.assertFalse((out/'captures/create-card').exists())
        self.assertEqual(self.client.started,0)

    def test_failed_collection_preserves_latest_and_never_executes(self):
        self.client.case_result['result']='FAILURE'
        lib=self.root/'library';replace_private_json(lib/'latest.json',{'unchanged':True})
        before=(lib/'latest.json').read_bytes()
        with self.assertRaisesRegex(core.Rejected,'execution or deployment'):
            writer.collect(self.client,self.plan,self.registry,{'create-card':{'run_id':30,'deployment':self.attestation()}},self.root/'collect',['media.example'])
        self.assertEqual((lib/'latest.json').read_bytes(),before)
        self.assertEqual(self.client.started,0)
        self.assertEqual(core.load_json(self.root/'collect/state.json')['phase'],'blocked')

del JourneyTests
