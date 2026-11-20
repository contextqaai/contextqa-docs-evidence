import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from cqa_artifacts import agent, core, journeys as j
from cqa_artifacts.contextqa import ContextQAClient
from cqa_artifacts.loop import Store, fingerprint

PASS={'status':'STATUS_COMPLETED','result':'SUCCESS','totalCount':1,'passedCount':1,'failedCount':0,'abortedCount':0,'stoppedCount':0,'notExecutedCount':0}

class FakeClient:
    transport_label='simulated'
    def __init__(self):
        self.calls=[];self.case={'id':10,'name':'Create card','workspaceVersionId':1,'videoRecording':True}
        self.step={'id':20,'testCaseId':10,'action':'Click Create card','position':1,'disabled':False}
        self.case_result=dict(PASS,id=100,testCaseId=10,testPlanResultId=30)
        self.step_result=dict(id=200,testCaseId=10,testCaseResultId=100,stepId=20,result='SUCCESS',stepDetails={'action':'Click Create card'},screenShotURL='https://media.example/s.png?private=secret')
        self.run={'id':30,'testPlanId':40,**PASS};self.plan={'id':40,'workspaceVersionId':1,'name':'Cards'}
        self.writes=0;self.started=0
    def call(self,operation,id=None,query=None,body=None,approve_write=False,**kwargs):
        self.calls.append((operation,id,query))
        if operation=='getTestCase':return copy.deepcopy(self.case)
        if operation=='getTestStep':return copy.deepcopy(self.step)
        if operation=='getTestPlan':return copy.deepcopy(self.plan)
        if operation=='getTestPlanResult':return copy.deepcopy(self.run)
        if operation=='getRunSummary':return copy.deepcopy(PASS)
        if operation=='getTestCaseResult':return copy.deepcopy(self.case_result)
        if operation=='getTestStepResult':return copy.deepcopy(self.step_result)
        if operation=='listTestCaseResults':return {'content':[copy.deepcopy(self.case_result)],'last':True}
        if operation=='listTestStepResults':return {'content':[copy.deepcopy(self.step_result)],'last':True}
        raise AssertionError(operation)
    def call_to_file(self,operation,destination,**options):
        self.writes+=1
        if operation=='updateTestStep':self.step.update(options['body'])
        elif operation=='updateTestCase':self.case.update(options['body'])
        else:raise AssertionError(operation)
        j.exclusive_json(destination,{'id':options['id']})
    def trigger_run(self,plan_id,journal,**kwargs):
        self.started+=1;j.journal_event(journal,{'state':'accepted','run_id':30},first=True)
        return {'run_id':30,'state':'accepted'}
    def poll_run(self,run_id,**kwargs):return {'run_id':run_id,'verdict':'passed','transport':'simulated'}

class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.repo=self.root/'repo';self.repo.mkdir()
        def git(*args):return subprocess.check_output(['git',*args],cwd=self.repo,text=True).strip()
        git('init','-q');git('config','user.name','Test');git('config','user.email','test@example.invalid')
        (self.repo/'code.py').write_text('old\n');(self.repo/'guide.md').write_text('# Guide\n\nKeep this introduction.\n')
        git('add','.');git('-c','core.hooksPath=/dev/null','commit','-qm','base');self.base=git('rev-parse','HEAD')
        (self.repo/'code.py').write_text('new\n');git('add','.');git('-c','core.hooksPath=/dev/null','commit','-qm','head');self.head=git('rev-parse','HEAD')
        self.manifest=dict(schema=1,project_id='cards',name='Cards',repository='example/cards',application_url='https://app.example',environment='qa',instructions='Use reviewed evidence',allow_simulated_evidence=True,
            sections=[dict(id='create',path='guide.md',title='Create a card',owner='owner',code_paths=['code.py'])])
        self.plan=agent.plan(self.repo,self.manifest,self.base,self.head)
        self.registry=dict(schema=1,repository='example/cards',journeys=[dict(id='create-card',name='Create a card',sections=['create'],code_paths=['code.py'],application_url='https://app.example',environment='qa',workspace_version_id=1,
            profile=dict(schema=1,name='Cards',plan={'id':40,'expect':{'workspaceVersionId':1}},cases=[{'id':10,'expect':{'workspaceVersionId':1,'name':'Create card'}}],steps=[{'id':20,'expect':{'testCaseId':10,'action':'Click Create card'}}]),case_ids=[10],required_media=['screenshot','video'])])
        self.client=FakeClient()
    def attestation(self):
        return dict(run_id=30,commit_sha=self.head,application_url='https://app.example',environment='qa',journey_digest=fingerprint(self.registry['journeys'][0]),verified_by='Synthetic test',evidence_ref='Synthetic deployment fixture',confirmed=True)
    def captured(self,attested=True):
        out=self.root/'capture';j.capture(self.client,self.registry,'create-card',30,self.head,out,self.attestation() if attested else None)
        return out
    def exported(self):
        root=self.captured()
        # Header-only synthetic media tests plumbing, never real pixel/video fidelity.
        screenshot=core.add_media_bytes(root,b'\x89PNG\r\n\x1a\nsynthetic','screenshot')
        video=core.add_media_bytes(root,b'\x00\x00\x00\x18ftypmp42synthetic','video')
        recipe={'steps':[dict(step_result_id=200,title='Create a card',instruction='Enter a title and select Create card. Recording 00:02 shows the new card.',media_ids=[screenshot,video])]}
        out=self.root/'export';j.review_capture(root,recipe,out,'Fixture reviewer',True)
        return out
    def test_impact_maps_changes_and_reports_missing_coverage(self):
        report=j.impact(self.plan,self.registry)
        self.assertEqual([x['id'] for x in report['journeys']],['create-card']);self.assertEqual(report['unmapped_sections'],[])
        p=copy.deepcopy(self.plan);p.pop('plan_digest');p['affected_sections'].append('rename');p=j.sealed(p,'plan_digest')
        self.assertEqual(j.impact(p,self.registry)['unmapped_sections'],['rename'])
    def test_registry_rejects_cross_workspace_duplicate_and_unmapped_cases(self):
        for mutate in [lambda r:r['journeys'].append(copy.deepcopy(r['journeys'][0])),lambda r:r['journeys'][0].update(case_ids=[11]),lambda r:r['journeys'][0].update(workspace_version_id=2)]:
            r=copy.deepcopy(self.registry);mutate(r)
            with self.assertRaises(core.Rejected):j.registry(r)
    def test_capture_automatically_selects_results_and_preserves_private_urls(self):
        root=self.captured();record=core.load_json(root/'journey-capture.json')
        self.assertEqual(record['receipt']['verdict'],'passed');self.assertTrue(record['deployment_verified'])
        self.assertNotIn('private=secret',json.dumps(record));self.assertIn('private=secret',(root/'private/artifact-references.json').read_text())
        self.assertEqual(core.manifest(root)['steps'][0]['step_result_id'],200)
    def test_wrong_run_plan_and_partial_steps_are_rejected(self):
        self.client.run['testPlanId']=999
        with self.assertRaises(core.Rejected):self.captured()
        self.client.run['testPlanId']=40;self.client.case_result['totalCount']=2
        with self.assertRaises(core.Rejected):self.captured()
    def test_unrelated_result_filter_is_rejected(self):
        self.client.step_result['testCaseResultId']=999
        with self.assertRaises(core.Rejected):self.captured()
    def test_missing_deployment_blocks_export(self):
        root=self.captured(False)
        with self.assertRaises(core.Rejected):j.review_capture(root,{'steps':[]},self.root/'export','Test',True)
    def test_failed_capture_is_retained_but_cannot_publish(self):
        self.client.case_result['result']='FAILURE'
        root=self.captured()
        self.assertEqual(core.load_json(root/'journey-capture.json')['receipt']['verdict'],'failed')
        with self.assertRaises(core.Rejected):j.review_capture(root,{'steps':[]},self.root/'export','Test',True)
    def test_drift_blocks_capture_before_writing_output(self):
        self.client.step['action']='Unreviewed action'
        with self.assertRaises(core.Rejected):self.captured()
        self.assertFalse((self.root/'capture').exists())
    def test_missing_required_video_blocks_review(self):
        root=self.captured();mid=core.add_media_bytes(root,b'\x89PNG\r\n\x1a\nsynthetic','screenshot')
        recipe={'steps':[dict(step_result_id=200,title='Create',instruction='Create a card',media_ids=[mid])]}
        with self.assertRaises(core.Rejected):j.review_capture(root,recipe,self.root/'export','Test',True)
    def test_wrong_step_association_blocks_review(self):
        root=self.captured();recipe={'steps':[dict(step_result_id=999,title='Create',instruction='Create',media_ids=[])]}
        with self.assertRaises(core.Rejected):j.review_capture(root,recipe,self.root/'export','Test',True)
    def test_complete_local_workflow_bundles_video_and_screenshot(self):
        export=self.exported();out=self.root/'review'
        receipt=j.prepare(self.plan,self.registry,{'create-card':str(export)},out)
        store=Store(out/'review.db');item=store.snapshot('cards','owner')['items'][receipt['item_id']]
        self.assertEqual(len(item['evidence']),1)
        draft=(out/'drafts/guide.md').read_text();self.assertIn('Keep this introduction.',draft);self.assertIn('.mp4)',draft);self.assertIn('.png)',draft)
        with self.assertRaises(core.Rejected):store.bundle('cards','owner',item['id'])
        item=store.review('cards','owner',item['id'],item['version'],'answer',text='Reviewed deployment, instructions and media')
        item=store.review('cards','owner',item['id'],item['version'],'accept',change_id='1')
        item=store.review('cards','owner',item['id'],item['version'],'ready')
        store.approve('cards','owner',item['id'],item['version'],True)
        bundle=store.bundle('cards','owner',item['id'])
        self.assertTrue(any(p.endswith('.mp4') for p in bundle['evidence_files']))
        self.assertTrue(any(p.endswith('.png') for p in bundle['evidence_files']))
        self.assertNotIn('private=secret',json.dumps(bundle))
        subprocess.run(['git','apply','--check',str(out/'changes.patch')],cwd=self.repo,check=True,capture_output=True)
    def test_refresh_replaces_managed_block_and_preserves_prose(self):
        export=self.exported();enriched=j.evidence_plan(self.plan,self.registry,{'create-card':str(export)})
        proposal=j.draft_from_evidence(enriched)
        second=copy.deepcopy(enriched);second.pop('plan_digest');second['articles'][0]['before']=proposal['edits'][0]['after']
        self.assertEqual(j.draft_from_evidence(j.sealed(second,'plan_digest'))['edits'],[])
    def test_stale_registry_and_revision_evidence_are_rejected(self):
        export=self.exported();r=copy.deepcopy(self.registry);r['journeys'][0]['name']='Different'
        with self.assertRaises(core.Rejected):j.evidence_plan(self.plan,r,{'create-card':str(export)})
        p=copy.deepcopy(self.plan);p.pop('plan_digest');p['head_sha']='b'*40;p=j.sealed(p,'plan_digest')
        with self.assertRaises(core.Rejected):j.evidence_plan(p,self.registry,{'create-card':str(export)})
    def test_one_journey_cannot_satisfy_another(self):
        export=self.exported();enriched=j.evidence_plan(self.plan,self.registry,{'create-card':str(export)})
        enriched.pop('plan_digest');other=dict(enriched['event']['journey_requirements'][0],journey_id='rename-card');enriched['event']['journey_requirements'].append(other)
        out=self.root/'review';receipt=agent.prepare(j.sealed(enriched,'plan_digest'),j.draft_from_evidence(j.sealed(enriched,'plan_digest')),out)
        store=Store(out/'review.db');item=store.attach_evidence('cards','owner',receipt['item_id'],1,export)
        with self.assertRaises(core.Rejected):store.review('cards','owner',item['id'],item['version'],'answer',text='All done')
    def test_maintenance_dry_run_drift_and_verified_next_registry(self):
        changes=[dict(kind='step',id=20,changes={'action':'Click Save card'},reason='Product label changed')]
        planned=j.maintenance_plan(self.client,self.registry,'create-card',changes)
        self.assertEqual(self.client.writes,0)
        with self.assertRaises(core.Rejected):j.apply_maintenance(self.client,self.registry,planned,self.root/'write')
        self.client.step['position']=2
        with self.assertRaises(core.Rejected):j.apply_maintenance(self.client,self.registry,planned,self.root/'write',True)
        self.assertEqual(self.client.writes,0);self.client.step['position']=1
        j.apply_maintenance(self.client,self.registry,planned,self.root/'write',True)
        self.assertEqual(self.client.writes,1)
        updated=core.load_json(self.root/'write/registry.next.json');self.assertEqual(updated['journeys'][0]['profile']['steps'][0]['expect']['action'],'Click Save card')
        with self.assertRaises(core.Rejected):j.apply_maintenance(self.client,self.registry,planned,self.root/'write',True)
        self.assertEqual(self.client.writes,1)
    def test_unregistered_resource_and_identity_changes_rejected(self):
        for changes in [[dict(kind='step',id=99,changes={'action':'Oops'},reason='test')],[dict(kind='step',id=20,changes={'testCaseId':99},reason='test')]]:
            with self.assertRaises(core.Rejected):j.maintenance_plan(self.client,self.registry,'create-card',changes)
    def test_run_requires_approval_and_never_replays_existing_intent(self):
        with self.assertRaises(core.Rejected):j.run(self.client,self.registry,'create-card',self.root/'run')
        j.run(self.client,self.registry,'create-card',self.root/'run',True)
        with self.assertRaises(core.Rejected):j.run(self.client,self.registry,'create-card',self.root/'run',True)
        self.assertEqual(self.client.started,1)
    def test_media_download_proposes_association_without_approval(self):
        root=self.captured()
        def fake_fetch(root,index,kind,host):
            return {'media_id':core.add_media_bytes(root,b'\x89PNG\r\n\x1a\nsynthetic','screenshot')}
        with patch('cqa_artifacts.media.fetch_media',side_effect=fake_fetch):result=j.fetch_capture_media(root,['media.example'])
        self.assertEqual(result['downloaded'],1);self.assertFalse(result['attached'])
        self.assertEqual(core.manifest(root)['steps'][0]['media'],[])
        self.assertEqual(len(core.load_json(root/'review-recipe.json')['steps'][0]['media_ids']),1)
    def test_registered_definition_lock_detects_unmapped_step_changes(self):
        original=self.client.call
        def call(operation,**kwargs):
            if operation=='listTestSteps':return {'content':[copy.deepcopy(self.client.step)],'last':True}
            return original(operation,**kwargs)
        self.client.call=call
        registered=j.register(self.client,self.registry,'create-card')
        self.assertEqual(len(registered['journeys'][0]['definition_locks']),2)
        j.inspect(self.client,registered['journeys'][0])
        self.client.step['event']={'selector':'unreviewed-selector'}
        with self.assertRaises(core.Rejected):j.inspect(self.client,registered['journeys'][0])
    def test_ambiguous_write_is_not_retried(self):
        changes=[dict(kind='step',id=20,changes={'action':'Click Save'},reason='Reviewed label change')]
        planned=j.maintenance_plan(self.client,self.registry,'create-card',changes)
        def ambiguous(*args,**kwargs):
            self.client.writes+=1
            raise core.Rejected('Acceptance unknown')
        self.client.call_to_file=ambiguous
        for attempt in range(2):
            with self.assertRaises(core.Rejected):j.apply_maintenance(self.client,self.registry,planned,self.root/'write',True)
        self.assertEqual(self.client.writes,1)

    def test_signed_screenshot_rotation_is_not_definition_drift(self):
        a=dict(self.client.step,goldenScreenshot='https://media.example/golden.png?signature=old')
        b=dict(a,goldenScreenshot='https://media.example/golden.png?signature=new')
        self.assertEqual(j.definition_digest('updateTestStep',a),j.definition_digest('updateTestStep',b))
        b['goldenScreenshot']='https://media.example/different.png?signature=new'
        self.assertNotEqual(j.definition_digest('updateTestStep',a),j.definition_digest('updateTestStep',b))
        b=dict(a,testData='https://app.example/?required=value')
        self.assertNotEqual(j.definition_digest('updateTestStep',a),j.definition_digest('updateTestStep',b))
    def test_collection_run_map_is_exact_and_never_starts_runs(self):
        with self.assertRaises(core.Rejected):j.collect(self.client,self.plan,self.registry,{},self.root/'collection')
        result=j.collect(self.client,self.plan,self.registry,{'create-card':{'run_id':30,'deployment':self.attestation()}},self.root/'collection')
        self.assertEqual(len(result['journeys']),1);self.assertEqual(self.client.started,0)
        self.assertTrue((self.root/'collection/collection.json').exists())

    def test_read_dto_nulls_are_projected_into_valid_write_dtos(self):
        from cqa_artifacts.contextqa import validate, OPERATIONS
        actual=dict(self.client.case,description=None,missingData={'prerequisiteMissingContent':None})
        body=j.writable('updateTestCase',actual)
        validate(body,OPERATIONS['updateTestCase']['body'])
        self.assertNotIn('description',body)
        self.assertNotIn('prerequisiteMissingContent',body['missingData'])
        self.assertEqual(body['name'],'Create card')

    def test_cli_impact_runs_without_token_or_server(self):
        for name,value in [('registry',self.registry),('plan',self.plan)]:j.exclusive_json(self.root/(name+'.json'),value)
        result=subprocess.run([sys.executable,'-m','cqa_artifacts.journeys','impact','--registry',str(self.root/'registry.json'),'--plan',str(self.root/'plan.json'),'--out',str(self.root/'impact.json')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

import sys
