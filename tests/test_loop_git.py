import tempfile
import unittest
from pathlib import Path
from cqa_artifacts.core import Rejected
from cqa_artifacts.loop import fingerprint
from cqa_artifacts.loop_git import deliver

class GitDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.sha='a'*40; self.calls=[]
        self.bundle={'published':False,'approval':{'digest':'reviewed'},'files':{'guide.md':'new\n'},'baseline':{'guide.md':fingerprint('old\n')},'item':'item','evidence_files':{}}
    def command(self,args,cwd):
        self.calls.append(args)
        if args[:3]==['git','remote','get-url']: return 'https://github.com/org/repo.git'
        if args[:2]==['git','rev-parse']:return self.sha
        if args[:2]==['git','ls-remote']:return self.sha+'\trefs/heads/main'
        if args[:2]==['git','ls-tree']:return '100644'
        if args[:2]==['git','show']:return 'old\n'
        if args[:2]==['git','clone']:Path(args[-1]).mkdir()
        if args[:3]==['gh','pr','create']:return 'https://github.com/org/repo/pull/42'
        return ''
    def deliver(self, **extra):
        return deliver(self.bundle,self.root,'org/repo',self.sha,'contextqa-docs/review-1',self.root/'journal',run=self.command,**extra)
    def test_approval_required_before_network(self):
        with self.assertRaises(Rejected):self.deliver()
        self.assertEqual([],self.calls)
    def test_draft_is_explicit_and_journal_prevents_replay(self):
        receipt=self.deliver(approved=True)
        self.assertFalse(receipt['published'])
        create=next(c for c in self.calls if c[0]=='gh')
        self.assertIn('--draft',create);self.assertEqual(create[create.index('--base')+1],'main')
        with self.assertRaises(Rejected):self.deliver(approved=True)
        self.assertIn('draft_pr_created',(self.root/'journal').read_text())
    def test_exact_baseline_blocks_push(self):
        self.bundle['baseline']['guide.md']=fingerprint('changed\n')
        with self.assertRaisesRegex(Rejected,'baseline'):self.deliver(approved=True)
        self.assertFalse(any(c[:2]==['git','push'] for c in self.calls))
    def test_failed_push_records_intent_and_requires_reconciliation(self):
        original=self.command
        def fail(args,cwd):
            if args[:2]==['git','push']:raise Rejected('network uncertain')
            return original(args,cwd)
        self.command=fail
        with self.assertRaises(Rejected):self.deliver(approved=True)
        self.assertIn('push_intent',(self.root/'journal').read_text())
        self.assertFalse(any(c[0]=='gh' for c in self.calls))
        with self.assertRaisesRegex(Rejected,'Journal'):self.deliver(approved=True)
    def test_media_requires_reviewed_content_addressed_path(self):
        self.bundle['evidence_files']={'media/image.png':'data'}
        with self.assertRaisesRegex(Rejected,'evidence path'):self.deliver(approved=True)
    def test_reviewed_media_is_included_in_draft_commit(self):
        import base64
        relative='evidence/'+'a'*64+'/assets/'+'b'*64+'.mp4'
        self.bundle['evidence_files']={relative:base64.b64encode(b'synthetic video').decode()}
        original=self.command
        def command(args,cwd):
            if args[:2]==['git','ls-tree'] and args[-1]==relative:return ''
            if args[:2]==['git','add']:
                self.assertIn(relative,args)
                self.assertEqual((cwd/relative).read_bytes(),b'synthetic video')
            return original(args,cwd)
        self.command=command
        self.assertEqual(self.deliver(approved=True)['stage'],'draft_pr_created')
    def test_hosted_guides_bind_repo_branch_and_root(self):
        destination=dict(docs_repo='org/repo',branch='main',docs_root='manual')
        self.bundle['source']={'documentation_destination':destination}
        with self.assertRaisesRegex(Rejected,'destination'):
            self.deliver(approved=True,current_destination={**destination,'docs_root':'elsewhere'})
        self.assertFalse(self.calls)
        self.assertEqual(self.deliver(approved=True,current_destination=destination)['stage'],'draft_pr_created')
        self.assertIn(['git','add','--','manual/guide.md'],self.calls)

    def test_remote_drift_blocks_delivery(self):
        original=self.command
        self.command=lambda args,cwd: ('b'*40+'\trefs/heads/main') if args[:2]==['git','ls-remote'] else original(args,cwd)
        with self.assertRaisesRegex(Rejected,'Remote target'):self.deliver(approved=True)
