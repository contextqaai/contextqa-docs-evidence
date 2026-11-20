import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from cqa_artifacts.agent import plan,validate_proposal,submit
from cqa_artifacts.core import Rejected
from cqa_artifacts.loop import Store

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        def git(*args):return subprocess.check_output(['git',*args],cwd=self.root,text=True).strip()
        self.git=git;git('init','-q');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid')
        (self.root/'code.py').write_text('label="Old"\n');(self.root/'guide.md').write_text('# Guide\nUse Old.\n');git('add','.');git('-c','core.hooksPath=/dev/null','commit','-qm','base');self.base=git('rev-parse','HEAD')
        (self.root/'code.py').write_text('label="New"\n');git('add','.');git('-c','core.hooksPath=/dev/null','commit','-qm','change');self.head=git('rev-parse','HEAD')
        self.manifest=dict(schema=1,project_id='test',name='Test',repository='example/test',application_url='https://example.invalid',environment='test',instructions='Use reviewed source',sections=[dict(id='guide',path='guide.md',title='Guide',owner='owner',code_paths=['code.py'])])
        self.plan=plan(self.root,self.manifest,self.base,self.head)
    def test_source_bound_plan_uses_committed_baseline(self):
        (self.root/'guide.md').write_text('Uncommitted unrelated text')
        fresh=plan(self.root,self.manifest,self.base,self.head)
        self.assertEqual(fresh['articles'][0]['before'],'# Guide\nUse Old.\n')
        self.assertIn('+label="New"',fresh['diff']);self.assertFalse(fresh['executed'])
    def test_proposal_cannot_change_execution_policy_or_paths(self):
        for proposal in [dict(edits=[],requires_capture=False),dict(edits=[dict(path='../../secret.md',after='text',reason='test')]),dict(edits=[dict(path='unmapped.md',after='text',reason='test')])]:
            with self.assertRaises(Rejected):validate_proposal(self.plan,proposal)
    def test_tampered_plan_rejected(self):
        self.plan['head_sha']='bad'
        with self.assertRaises(Rejected):validate_proposal(self.plan,{'edits':[]})
    def test_questions_remain_a_review_gate(self):
        proposal=dict(title='Update guide',summary='Source label changed',edits=[dict(path='guide.md',after='# Guide\nUse New.\n',reason='Label changed in source')],questions=['Is the deployment updated?'])
        event=validate_proposal(self.plan,proposal)
        self.assertTrue(event['requires_capture']);self.assertEqual(event['edits'][0]['before'],'# Guide\nUse Old.\n')
        store=Store(self.root/'state.db');store.create(self.manifest);store.article('test','owner','guide.md','Guide','# Guide\nUse Old.\n')
        item=store.ingest('test','owner',event)['item_id'];state=store.snapshot('test','owner')
        self.assertIn('Is the deployment updated?',state['items'][item]['questions'])
    def test_moving_refs_and_unsafe_submission_origins_rejected(self):
        with self.assertRaises(Rejected):plan(self.root,self.manifest,'main',self.head)
        for url in ['http://example.com','https://user:secret@example.com','https://example.com/path']:
            with self.assertRaises(Rejected):submit({},url,'org','project','token')
    def test_duplicate_proposal_ids_stable_revision_new(self):
        p=dict(edits=[]);a=validate_proposal(self.plan,p);b=validate_proposal(self.plan,p)
        self.assertEqual(a['id'],b['id']);self.assertNotEqual(a['id'],validate_proposal(self.plan,dict(edits=[],questions=['Need context']))['id'])
    def test_question_bounds_match_review_ingestion(self):
        store=Store(self.root/'bounds.db');store.create(self.manifest);store.article('test','owner','guide.md','Guide','# Guide\nUse Old.\n')
        edit=dict(path='guide.md',after='# Guide\nUse New.\n',reason='Label changed in source')
        accepted=validate_proposal(self.plan,dict(edits=[edit],questions=['q'*500]))
        item=store.ingest('test','owner',accepted)['item_id']
        self.assertIn('q'*500,store.snapshot('test','owner')['items'][item]['questions'])
        for questions in (['q'*501],['q']*201,[''],[7]):
            with self.assertRaises(Rejected):validate_proposal(self.plan,dict(edits=[edit],questions=questions))

    def test_plan_preserves_article_edits_already_in_target_commit(self):
        (self.root/'guide.md').write_text('# Guide\nAlready updated in source PR.\n')
        self.git('add','.');self.git('-c','core.hooksPath=/dev/null','commit','-qm','article in source PR')
        head=self.git('rev-parse','HEAD')
        planned=plan(self.root,self.manifest,self.base,head)
        self.assertEqual(planned['articles'][0]['before'],'# Guide\nAlready updated in source PR.\n')

    def test_real_cli_writes_plan_file(self):
        config=self.root/'manifest.json';config.write_text(json.dumps(self.manifest));out=self.root/'plan.json'
        import sys
        result=subprocess.run([sys.executable,'-m','cqa_artifacts.agent','plan','--repo',str(self.root),'--config',str(config),'--base',self.base,'--head',self.head,'--out',str(out)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(out.read_text())['head_sha'],self.head)

    def test_prepare_creates_app_free_review_and_applicable_patch(self):
        from cqa_artifacts.agent import prepare
        proposal=dict(edits=[dict(path='guide.md',after='# Guide\nUse New.',reason='Changed source label')])
        out=self.root/'review-output';receipt=prepare(self.plan,proposal,out)
        self.assertFalse(receipt['approved']);self.assertFalse(receipt['published'])
        self.assertEqual(receipt['status'],'needs_input')
        self.assertEqual((out/'drafts/guide.md').read_text(),'# Guide\nUse New.')
        subprocess.run(['git','apply','--check',str(out/'changes.patch')],cwd=self.root,check=True,capture_output=True)
        state=Store(out/'review.db').snapshot('test','owner')
        with self.assertRaises(Rejected):Store(out/'review.db').bundle('test','owner',receipt['item_id'])
        with self.assertRaises(Rejected):prepare(self.plan,proposal,out)

    def test_prepare_rejects_invalid_proposal_before_writing(self):
        from cqa_artifacts.agent import prepare
        out=self.root/'bad-review'
        with self.assertRaises(Rejected):prepare(self.plan,{'edits':[{'path':'other.md','after':'text','reason':'test'}]},out)
        self.assertFalse(out.exists())

    def test_prepare_new_mdx_page_patch_applies(self):
        from cqa_artifacts.agent import prepare
        self.manifest['sections'][0]['path']='docs/guide.mdx'
        planned=plan(self.root,self.manifest,self.base,self.head)
        proposal=dict(edits=[dict(path='docs/guide.mdx',after='---\ntitle: Guide\n---\n\nUse New.\n',reason='Document source change')])
        out=self.root/'mdx-review'
        prepare(planned,proposal,out)
        subprocess.run(['git','apply','--check',str(out/'changes.patch')],cwd=self.root,check=True,capture_output=True)
        self.assertTrue((out/'drafts/docs/guide.mdx').exists())
