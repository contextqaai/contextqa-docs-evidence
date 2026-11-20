"""Explicit GitHub draft-PR delivery using an installed, authenticated gh CLI.

No branch merge, no site publication, no automatic retry after a remote write.
The local checkout is read; changes are assembled in a new temporary clone.
"""
import json
import base64
import os
from pathlib import Path
import re
import subprocess
import tempfile
from .core import Rejected
from .loop import fingerprint, path_name


def command(args,cwd):
    result=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=90,check=False,
        env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GH_PROMPT_DISABLED':'1'})
    if result.returncode:
        raise Rejected('Delivery command failed: '+args[0]+' '+args[1]+'; inspect the journal before retrying')
    return result.stdout if args[:2]==['git','show'] else result.stdout.strip()


def deliver(bundle,checkout,repository,base_sha,branch,journal,approved=False,run=command,base_ref="main"):
    if approved is not True:
        raise Rejected('Explicit draft-PR delivery approval required')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise Rejected('Invalid GitHub repository')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]{0,199}',base_ref) or '..' in base_ref or '@{' in base_ref or base_ref.endswith(('/', '.')):
        raise Rejected('Invalid target branch')
    if not re.fullmatch(r'[a-f0-9]{40}',base_sha):
        raise Rejected('Use the full reviewed base commit SHA')
    if not re.fullmatch(r'contextqa-docs/[a-zA-Z0-9-]{1,80}',branch):
        raise Rejected('Use a unique contextqa-docs/ branch')
    if bundle.get('published') is not False or not bundle.get('approval') or not bundle.get('files'):
        raise Rejected('Reviewed draft bundle required')
    evidence={}
    for relative,payload in bundle.get('evidence_files',{}).items():
        if not re.fullmatch(r'evidence/[a-f0-9]{64}/(?:index\.html|manifest\.json|assets/(?:contextqa-logo\.svg|[a-f0-9]{64}\.(?:png|jpg|webp|mp4|webm)))',relative):
            raise Rejected('Invalid reviewed evidence path')
        try:evidence[relative]=base64.b64decode(payload,validate=True)
        except (ValueError,TypeError):raise Rejected('Invalid evidence bytes') from None
    if sum(map(len,evidence.values()))>16*1024*1024:
        raise Rejected('Reviewed evidence exceeds the 16 MiB delivery limit')
    journal=Path(journal)
    if journal.exists() or journal.is_symlink():
        raise Rejected('Journal already exists; reconcile remote state instead of replaying delivery')
    checkout=Path(checkout).resolve()
    origin=run(['git','remote','get-url','origin'],checkout)
    allowed=('https://github.com/'+repository+'.git','https://github.com/'+repository,'git@github.com:'+repository+'.git')
    if origin not in allowed:
        raise Rejected('Checkout origin does not match the reviewed GitHub repository')
    if run(['git','rev-parse','HEAD'],checkout)!=base_sha:
        raise Rejected('Checkout differs from reviewed base commit')
    remote=run(['git','ls-remote','--heads','origin','refs/heads/'+base_ref],checkout)
    if remote.split() != [base_sha,'refs/heads/'+base_ref]:
        raise Rejected('Remote target branch differs from the reviewed base commit')
    # Compare exact file contents at the commit, not an unrelated working tree.
    for relative in bundle['files']:
        path_name(relative)
        tracked=run(['git','ls-tree','--format=%(objectmode)','HEAD','--',relative],checkout)
        if tracked and tracked not in ('100644','100755'):
            raise Rejected('Destination must be an ordinary tracked file')
        current=run(['git','show',f'HEAD:{relative}'],checkout) if tracked else ''
        if fingerprint(current)!=bundle['baseline'][relative]:
            raise Rejected('Destination content differs from reviewed article baseline')
    for relative in evidence:
        # Content-addressed paths must be new. Never overwrite an existing asset,
        # even when a malicious checkout has placed a symlink at that path.
        if run(['git','ls-tree','--format=%(objectmode)','HEAD','--',relative],checkout):
            raise Rejected('Evidence destination already exists; use a fresh reviewed delivery')
    journal.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(journal,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    def record(value):
        with os.fdopen(os.dup(fd),'a') as f:
            f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
    try:
        record(dict(stage='intent',repository=repository,branch=branch,base_sha=base_sha,bundle_sha256=fingerprint(bundle)))
        with tempfile.TemporaryDirectory(prefix='contextqa-draft-') as temp:
            root=Path(temp)/'repo'
            run(['git','clone','--no-hardlinks','--no-checkout',str(checkout),str(root)],checkout)
            run(['git','checkout','-b',branch,base_sha],root)
            run(['git','remote','set-url','origin',origin],root)
            for relative,body in bundle['files'].items():
                destination=root/relative
                for ancestor in [destination,*destination.parents]:
                    if ancestor==root:break
                    if ancestor.is_symlink():raise Rejected('Destination has a symbolic-link component')
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_text(body)
            for relative,payload in evidence.items():
                destination=root/relative
                for ancestor in [destination,*destination.parents]:
                    if ancestor==root:break
                    if ancestor.is_symlink():raise Rejected('Evidence destination has a symbolic-link component')
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(payload)
            run(['git','add','--',*bundle['files'],*evidence],root)
            run(['git','-c','core.hooksPath=/dev/null','commit','-m','docs: apply reviewed ContextQA update'],root)
            record(dict(stage='push_intent'))
            run(['git','push','origin',branch],root)
            record(dict(stage='pushed'))
            bodyfile=Path(temp)/'pr-body.md'
            bodyfile.write_text('Reviewed ContextQA documentation update.\n\nSource item: '+bundle['item']+'\nApproval digest: '+bundle['approval']['digest']+'\n\nHuman review and merge are required. No site publication is performed by this tool.\n')
            record(dict(stage='pr_intent'))
            url=run(['gh','pr','create','--repo',repository,'--head',branch,'--base',base_ref,'--draft','--title','docs: reviewed ContextQA update','--body-file',str(bodyfile)],root)
            if not url.startswith('https://github.com/'+repository+'/pull/'):
                raise Rejected('PR response was not recognized; reconcile the recorded branch')
            receipt=dict(stage='draft_pr_created',url=url,repository=repository,branch=branch,published=False)
            record(receipt)
            return receipt
    finally:os.close(fd)
