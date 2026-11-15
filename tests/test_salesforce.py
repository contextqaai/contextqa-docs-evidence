import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import unittest
from cqa_artifacts.salesforce import prepare, draft_guide
from cqa_artifacts.core import Rejected

ROOT=Path(__file__).resolve().parents[1]
class SalesforcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'examples/salesforce/catalog.json').read_text())
        self.context=json.loads((ROOT/'examples/salesforce/context.synthetic.json').read_text())
        self.now=datetime(2026,11,14,12,tzinfo=timezone.utc)
    def test_only_independently_confirmed_scenario_is_reviewable(self):
        result=prepare(self.catalog,self.context,self.now)
        self.assertEqual(result['summary']['readyForReview'],1)
        self.assertFalse(result['executionAuthorized'])
        self.assertTrue(all(r['proof']=='not_checked' and not r['executed'] for r in result['scenarios']))
    def test_schema_field_named_password_is_not_a_credential(self):
        self.context['objects']['Lead']['fields']['Password']={'type':'string'}
        self.assertEqual(prepare(self.catalog,self.context,self.now)['summary']['readyForReview'],1)
        self.context['objects']['Lead']['fields']['Password']={'password':'must-not-export'}
        with self.assertRaises(Rejected):prepare(self.catalog,self.context,self.now)
    def test_missing_intent_and_wrong_environment_block(self):
        for modify in [lambda c:c['rules'].clear(),lambda c:c['environment'].update(isSandbox=False),lambda c:c['personas'].clear()]:
            c=copy.deepcopy(self.context);modify(c)
            self.assertEqual(prepare(self.catalog,c,self.now)['summary']['readyForReview'],0)
    def test_stale_and_future_context_block(self):
        for date in [self.now-timedelta(days=15),self.now+timedelta(days=1)]:
            c=copy.deepcopy(self.context);c['capturedAt']=date.isoformat()
            self.assertEqual(prepare(self.catalog,c,self.now)['summary']['readyForReview'],0)
    def test_secrets_and_duplicate_asset_ids_rejected(self):
        c=copy.deepcopy(self.context);c['client_secret']='never-export'
        with self.assertRaises(Rejected):prepare(self.catalog,c,self.now)
        catalog=copy.deepcopy(self.catalog);catalog['assets'].append(catalog['assets'][0])
        with self.assertRaises(Rejected):prepare(catalog,self.context,self.now)
    def test_draft_is_not_approved_or_executed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'draft';draft_guide(prepare(self.catalog,self.context,self.now),root)
            self.assertFalse((root/'approval.json').exists())
            self.assertIn('not executed',(root/'manifest.json').read_text())
    def test_unconfirmed_object_mapping_cannot_make_asset_ready(self):
        c=copy.deepcopy(self.context);c['objects']['Prospect__c']=c['objects'].pop('Lead')
        c['mappings']={'Lead':{'target':'Prospect__c','status':'suggested'}}
        self.assertEqual(prepare(self.catalog,c,self.now)['summary']['readyForReview'],0)
        c['mappings']['Lead']['status']='confirmed'
        self.assertEqual(prepare(self.catalog,c,self.now)['summary']['readyForReview'],1)

class Sx360ImportTests(unittest.TestCase):
    def test_only_fresh_schema_is_imported_never_code_or_intent(self):
        from cqa_artifacts.salesforce import context_from_sx360
        snapshot={'orgId':'synthetic','runId':'scan-1','completedAt':'2026-11-14T00:00:00Z','complete':False,'components':[
            {'type':'CustomObject','fullName':'Account','content':{}},
            {'type':'CustomField','fullName':'Account.Name','content':{'type':'string','length':255,'secret':'must-not-copy'}},
            {'type':'CustomField','fullName':'Account.Stale__c','stale':True,'content':{'type':'string'}},
            {'type':'ApexClass','content':{'Body':'private-source-must-not-copy'}}]}
        result=context_from_sx360(snapshot)
        self.assertEqual(result['objects']['Account']['fields']['Name']['length'],255)
        self.assertNotIn('must-not-copy',json.dumps(result))
        self.assertNotIn('Stale__c',json.dumps(result))
        self.assertEqual(result['rules'],{})
        self.assertIsNone(result['environment']['isSandbox'])
    def test_unhydrated_snapshot_fails_explicitly(self):
        from cqa_artifacts.salesforce import context_from_sx360
        with self.assertRaises(Rejected):
            context_from_sx360({'orgId':'x','runId':'x','completedAt':'x','components':[{'type':'CustomObject','fullName':'Account','blob':'hash'}]})
