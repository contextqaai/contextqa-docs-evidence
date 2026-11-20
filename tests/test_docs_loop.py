import copy
import hashlib
import hmac
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import zipfile
from cqa_artifacts.core import Rejected
from cqa_artifacts.loop import Store, fingerprint
from cqa_artifacts.docs_loop import make_server, package_bundle
from cqa_artifacts.loop_sources import github_event, transcript_event


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'state.db'; self.store=Store(self.db)
        self.manifest=json.loads((Path(__file__).parents[1]/'examples/docs-loop/manifest.json').read_text())
        self.store.create(self.manifest)
        self.store.article('demo','owner','guides/projects.md','Projects','Old text\n')
        self.event=dict(id='e1',source='manual',title='Project change',text='New label',module_ids=['projects'],edits=[dict(path='guides/projects.md',before='Old text\n',after='New text\n',reason='Approved product change')])
    def item(self,event=None):
        return self.store.ingest('demo','owner',event or self.event)['item_id']
    def ready(self,item):
        i=self.store.review('demo','owner',item,1,'accept',change_id='1')
        return self.store.review('demo','owner',item,i['version'],'ready')
    def approved(self):
        item=self.item(); i=self.ready(item)
        self.store.approve('demo','owner',item,i['version'],True)
        return item
    def test_full_loop_persists_and_does_not_publish(self):
        item=self.approved(); bundle=self.store.bundle('demo','owner',item)
        self.assertFalse(bundle['published'])
        with zipfile.ZipFile(io.BytesIO(package_bundle(bundle))) as z:
            self.assertEqual(z.read('docs/guides/projects.md'),b'New text\n')
        self.assertEqual(self.store.snapshot('demo','owner')['articles']['guides/projects.md']['body'],'Old text\n')
        self.store.apply_local('demo','owner',item,True)
        self.assertEqual(Store(self.db).snapshot('demo','owner')['articles']['guides/projects.md']['body'],'New text\n')
    def test_event_replay_and_collision(self):
        item=self.item(); self.assertTrue(self.store.ingest('demo','owner',self.event)['duplicate'])
        changed=copy.deepcopy(self.event); changed['text']='Other'
        with self.assertRaises(Rejected): self.item(changed)
        self.assertEqual(len(self.store.snapshot('demo','owner')['items']),1)
    def test_concurrent_duplicate(self):
        results=[]
        threads=[threading.Thread(target=lambda:results.append(Store(self.db).ingest('demo','owner',self.event))) for _ in range(5)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(results),5)
        self.assertEqual(sum(not r['duplicate'] for r in results),1)
    def test_roles_and_assignment(self):
        item=self.item(); self.store.member('demo','owner','alice','contributor')
        self.assertEqual(self.store.snapshot('demo','alice')['items'],{})
        with self.assertRaises(Rejected): self.store.review('demo','alice',item,1,'accept',change_id='1')
        i=self.store.review('demo','owner',item,1,'assign',assignee='alice')
        i=self.store.review('demo','alice',item,i['version'],'accept',change_id='1')
        i=self.store.review('demo','alice',item,i['version'],'ready')
        with self.assertRaises(Rejected): self.store.approve('demo','alice',item,i['version'],True)
        with self.assertRaises(Rejected): self.store.bundle('demo','alice',item)
    def test_cross_project_isolation(self):
        item=self.item(); m=copy.deepcopy(self.manifest); m['project_id']='other'; self.store.create(m,'bob')
        with self.assertRaises(Rejected): self.store.snapshot('demo','bob')
        with self.assertRaises(Rejected): self.store.review('other','bob',item,1,'accept',change_id='1')
    def test_unreviewed_delivery_rejected(self):
        item=self.item()
        with self.assertRaises(Rejected): self.store.bundle('demo','owner',item)
        with self.assertRaises(Rejected): self.store.review('demo','owner',item,1,'ready')
    def test_edit_invalidates_approval(self):
        item=self.approved(); i=self.store.snapshot('demo','owner')['items'][item]
        self.store.review('demo','owner',item,i['version'],'edit',change_id='1',after='Third text')
        with self.assertRaises(Rejected): self.store.bundle('demo','owner',item)
    def test_comment_invalidates_approval(self):
        item=self.approved(); i=self.store.snapshot('demo','owner')['items'][item]
        self.store.review('demo','owner',item,i['version'],'comment',text='Needs another look')
        with self.assertRaises(Rejected): self.store.bundle('demo','owner',item)
    def test_stale_review_version(self):
        item=self.item();self.store.review('demo','owner',item,1,'accept',change_id='1')
        with self.assertRaises(Rejected):self.store.review('demo','owner',item,1,'ignore',change_id='1')
    def test_upstream_drift_blocks_delivery(self):
        item=self.approved();self.store.article('demo','owner','guides/projects.md','Projects','Other edit',fingerprint('Old text\n'))
        with self.assertRaises(Rejected):self.store.bundle('demo','owner',item)
    def test_upstream_drift_blocks_apply(self):
        item=self.approved();self.store.bundle('demo','owner',item)
        self.store.article('demo','owner','guides/projects.md','Projects','Other edit',fingerprint('Old text\n'))
        with self.assertRaises(Rejected):self.store.apply_local('demo','owner',item,True)
    def test_article_optimistic_lock(self):
        with self.assertRaises(Rejected):self.store.article('demo','owner','guides/projects.md','Projects','Other')
    def test_missing_evidence_stays_needs_input(self):
        e=copy.deepcopy(self.event);e['requires_capture']=True;item=self.item(e)
        self.assertEqual(self.store.snapshot('demo','owner')['items'][item]['status'],'needs_input')
        with self.assertRaises(Rejected):self.store.review('demo','owner',item,1,'answer',text='Pretend it passed')
    def test_missing_relevance_is_not_no_change(self):
        e=dict(id='unmapped',source='manual',title='Unknown feature',text='Needs coverage')
        item=self.item(e);self.assertEqual(self.store.snapshot('demo','owner')['items'][item]['status'],'needs_input')
    def test_exact_unchanged_edit_no_change(self):
        e=copy.deepcopy(self.event);e['edits'][0]['after']=e['edits'][0]['before']
        item=self.item(e);self.assertEqual(self.store.snapshot('demo','owner')['items'][item]['status'],'no_change')
    def test_path_escape(self):
        e=copy.deepcopy(self.event);e['edits'][0]['path']='../../secret.md'
        with self.assertRaises(Rejected):self.item(e)
    def test_event_stale_base(self):
        e=copy.deepcopy(self.event);e['edits'][0]['before']='Wrong'
        with self.assertRaises(Rejected):self.item(e)
    def test_partial_review_only_accepted_delivered(self):
        e=copy.deepcopy(self.event);e['edits'].append(dict(path='guides/new.md',before='',after='New page',reason='New feature'))
        item=self.item(e);i=self.store.review('demo','owner',item,1,'accept',change_id='1')
        i=self.store.review('demo','owner',item,i['version'],'ignore',change_id='2')
        i=self.store.review('demo','owner',item,i['version'],'ready');self.store.approve('demo','owner',item,i['version'],True)
        self.assertEqual(list(self.store.bundle('demo','owner',item)['files']),['guides/projects.md'])
    def test_audit(self):
        self.store.article('demo','owner','guides/links.md','Links','[Bad](missing.md) [Remote](https://example.com)')
        issues=self.store.audit('demo','owner')['issues']
        self.assertTrue(any(i['kind']=='coverage_gap' for i in issues))
        self.assertEqual(sum(i['kind']=='broken_internal_link' for i in issues),1)
    def test_delivered_cannot_be_edited(self):
        item=self.approved();self.store.bundle('demo','owner',item);i=self.store.snapshot('demo','owner')['items'][item]
        with self.assertRaises(Rejected):self.store.review('demo','owner',item,i['version'],'edit',change_id='1',after='Tampered')
    def test_webhook_signature_scope_and_merge(self):
        d=dict(action='closed',repository=dict(full_name='example/product',default_branch='main'),pull_request=dict(merged=True,title='Change',body='Details',base=dict(ref='main'),html_url='https://github.com/example/product/pull/1',merge_commit_sha='abc'))
        raw=json.dumps(d).encode(); secret='x'*32;sig='sha256='+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
        self.assertEqual(github_event(raw,sig,secret,'example/product','123')['source'],'github')
        with self.assertRaises(Rejected):github_event(raw,'wrong',secret,'example/product','123')
        with self.assertRaises(Rejected):github_event(raw,sig,secret,'other/repo','123')
    def test_transcript_requires_verbatim_segment(self):
        segment=dict(title='New project',start_seconds=1,end_seconds=20,excerpt='Observed change')
        self.assertEqual(len(transcript_event('v','Video','Observed change',[segment],'https://example.com/video')),1)
        segment['excerpt']='Invented evidence'
        with self.assertRaises(Rejected):transcript_event('v','Video','Observed change',[segment],'https://example.com/video')
    def test_http_auth_origin_and_crud(self):
        server=make_server(self.store,'demo','owner',0,'test-token'); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_port}'
        def req(path,headers=None,data=None):
            return urllib.request.urlopen(urllib.request.Request(base+path,headers=headers or {},data=data),timeout=3)
        for headers in ({},{'Authorization':'Bearer test-token','Origin':'https://evil.example'}):
            try: req('/api/state',headers)
            except urllib.error.HTTPError as exc:
                self.assertEqual(exc.code,403); exc.close()
            else: self.fail('Unauthorized request succeeded')
        with req('/api/state',{'Authorization':'Bearer test-token'}) as r:self.assertEqual(json.load(r)['role'],'admin')
        with req('/api/events',{'Authorization':'Bearer test-token','Content-Type':'application/json'},json.dumps(self.event).encode()) as r:self.assertIn('item_id',json.load(r))
        with req('/') as r:self.assertIn(b'ContextQA',r.read())

if __name__=='__main__':unittest.main()
