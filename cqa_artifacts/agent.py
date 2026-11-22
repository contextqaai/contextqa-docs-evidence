"""Repository-native documentation agent: plan, validate a draft, submit for review."""
import argparse
import copy
import difflib
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from .core import Rejected
from .loop import encoded, fingerprint, validate_manifest, path_name, text, strings, LIST_LIMIT, LIST_ITEM_LIMIT

MAX_CONTEXT=120000

def git(repo,*args):
    result=subprocess.run(['git','--no-pager',*args],cwd=repo,capture_output=True,timeout=30,check=False,
                          env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_NOSYSTEM':'1'})
    if result.returncode:raise Rejected('Git could not read the requested revision or path')
    if len(result.stdout)>MAX_CONTEXT:raise Rejected('Source exceeds context limit; narrow the change before drafting')
    return result.stdout.decode('utf-8',errors='strict')

def revision(repo,value):
    if not re.fullmatch(r'[a-fA-F0-9]{7,40}',value):raise Rejected('Use immutable commit SHAs, not moving branch names')
    return git(repo,'rev-parse','--verify',value+'^{commit}').strip()

def plan(repo,manifest,base,head,source_url=None):
    manifest=validate_manifest(manifest);repo=Path(repo).resolve()
    base=revision(repo,base);head=revision(repo,head)
    paths=[p for p in git(repo,'diff','--name-only','-z',base,head,'--').split('\0') if p]
    affected=[s for s in manifest['sections'] if any(fnmatch.fnmatchcase(p,glob) for p in paths for glob in s.get('code_paths',[]))]
    articles=[]
    for section in affected:
        path=path_name(section['path'])
        # Preserve documentation edits already made by the source PR. Delivery
        # will target the head revision, not overwrite it with the older base.
        mode=git(repo,'ls-tree','--format=%(objectmode)',head,'--',path).strip()
        if mode and mode not in ('100644','100755'):raise Rejected('Article must be a regular file')
        body=git(repo,'show',head+':'+path) if mode else ''
        articles.append(dict(path=path,title=section['title'],before=body,base_digest=fingerprint(body)))
    diff=git(repo,'diff','--no-ext-diff','--no-textconv','--unified=5',base,head,'--')
    event=dict(id='git:'+manifest['repository']+':'+base+':'+head,source='github',title='Documentation impact for '+head[:7],
               text='Review documentation affected by source changes from '+base[:7]+' to '+head[:7]+'.',revision=head,
               changed_paths=paths,edits=[],requires_capture=manifest.get('require_capture',True),requires_screenshots=manifest.get('require_screenshots',False))
    if source_url:event['source_url']=source_url
    result=dict(schema=1,manifest=manifest,event=event,base_sha=base,head_sha=head,articles=articles,diff=diff,
                affected_sections=[s['id'] for s in affected],review_required=True,executed=False)
    if len(encoded(result).encode())>MAX_CONTEXT:raise Rejected('Combined source context exceeds 120 KB; narrow the mapped change')
    result['plan_digest']=fingerprint(result)
    return result

def validate_proposal(planned,proposal):
    source=copy.deepcopy(planned);digest=source.pop('plan_digest',None)
    if digest!=fingerprint(source):raise Rejected('Plan integrity check failed; regenerate from the source revisions')
    if not isinstance(proposal,dict) or set(proposal)-{'title','summary','edits','questions'}:raise Rejected('Unexpected proposal fields')
    edits=proposal.get('edits')
    if not isinstance(edits,list) or len(edits)>200:raise Rejected('Proposal needs an edits list')
    articles={a['path']:a for a in source['articles']};seen=set();validated=[]
    for edit in edits:
        if not isinstance(edit,dict) or set(edit)!={'path','after','reason'}:raise Rejected('Each edit needs only path, after and reason')
        path=path_name(edit['path'])
        if path not in articles or path in seen:raise Rejected('Proposal must use unique affected article paths from this plan')
        seen.add(path);text(edit['after'],'proposed article');text(edit['reason'],'change rationale',2000)
        validated.append(dict(path=path,before=articles[path]['before'],after=edit['after'],reason=edit['reason']))
    event=copy.deepcopy(source['event'])
    event['title']=text(proposal.get('title',event['title']),'title',250)
    event['text']=text(proposal.get('summary',event['text']),'summary',10000)
    event['edits']=validated
    questions=proposal.get('questions',[])
    # Same bounds as review ingestion, so a validated proposal cannot fail later at submission.
    if not isinstance(questions,list) or len(questions)>LIST_LIMIT:raise Rejected(f'Use at most {LIST_LIMIT} proposal questions')
    if any(isinstance(q,str) and len(q)>LIST_ITEM_LIMIT for q in questions):raise Rejected(f'Each proposal question must be at most {LIST_ITEM_LIMIT} characters')
    event['agent_questions']=strings(questions,'proposal question')
    event['agent_plan_digest']=digest
    # Source ID is stable across retries, but a revised proposal gets a fresh review request.
    event['id']+=':proposal:'+fingerprint(proposal)[:16]
    return event

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def _post_source(url,organization,project,endpoint,payload,headers):
    parsed=urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise Rejected('Use an application origin without credentials, path, query or fragment')
    if parsed.scheme!='https' and not(parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost')):
        raise Rejected('Submission requires HTTPS (loopback development excepted)')
    for key in (organization,project):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key):raise Rejected('Invalid organization/project identifier')
    if len(payload)>2*1024*1024:raise Rejected('Event exceeds API limit')
    req=Request(url.rstrip('/')+'/api/orgs/'+organization+'/projects/'+project+'/'+endpoint,data=payload,
                headers={'Content-Type':'application/json',**headers})
    try:
        with build_opener(NoRedirect).open(req,timeout=30) as response:
            body=response.read(100000)
            return json.loads(body)
    except Exception:
        raise Rejected('Submission failed; inspect the inbox before retrying. The event ID makes identical replay idempotent.') from None

def submit(event,url,organization,project,token):
    if not token or '\n' in token or '\r' in token:raise Rejected('DOCS_AGENT_TOKEN is required')
    return _post_source(url,organization,project,'events',encoded(event).encode(),{'Authorization':'Bearer '+token})


def intake(payload,url,organization,project,kind,delivery,secret):
    import hmac
    if not secret or len(secret)<24:raise Rejected('DOCS_WEBHOOK_SECRET must be configured')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,120}',delivery):raise Rejected('Invalid delivery identifier')
    signature='sha256='+hmac.digest(secret.encode(),payload,'sha256').hex()
    return _post_source(url,organization,project,'github/webhook',payload,{'X-GitHub-Event':kind,
        'X-GitHub-Delivery':delivery,'X-Hub-Signature-256':signature})


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'x',opener=lambda p,flags:os.open(p,flags,0o600)) as f:f.write(json.dumps(value,indent=2)+'\n')

def prepare(planned, proposal, output):
    """Prepare a reviewable local change set without any app or external service.

    Draft files and patch are NOT an approved delivery. The existing domain
    store retains all evidence/question/approval gates for subsequent review.
    """
    from .loop import Store
    event=validate_proposal(planned,proposal)
    root=Path(output).resolve()
    if root.exists():raise Rejected('Choose a new output directory; prior review evidence is preserved')
    root.mkdir(parents=True,mode=0o700)
    manifest=planned['manifest'];project=manifest['project_id']
    store=Store(root/'review.db');store.create(manifest)
    for article in planned['articles']:
        if article['before']:
            store.article(project,'owner',article['path'],article['title'],article['before'])
    item_id=store.ingest(project,'owner',event)['item_id']
    patches=[]
    for edit in event['edits']:
        if edit['before']==edit['after']:continue
        path=edit['path'];destination=root/'drafts'/path
        destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with open(destination,'x',opener=lambda p,f:os.open(p,f,0o600)) as f:f.write(edit['after'])
        patches.append(f'diff --git a/{path} b/{path}\n')
        if not edit['before']:patches.append('new file mode 100644\n')
        diff=difflib.unified_diff(edit['before'].splitlines(True),edit['after'].splitlines(True),
                                 fromfile='a/'+path if edit['before'] else '/dev/null',tofile='b/'+path)
        for line in diff:
            patches.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    patch=''.join(patches)
    with open(root/'changes.patch','x',opener=lambda p,f:os.open(p,f,0o600)) as f:f.write(patch)
    write_new(root/'plan.json',planned);write_new(root/'proposal.json',proposal);write_new(root/'event.json',event)
    item=store.snapshot(project,'owner')['items'][item_id]
    receipt=dict(schema=1,project=project,item_id=item_id,source_url=event.get('source_url'),
                 base_sha=planned['base_sha'],head_sha=planned['head_sha'],plan_digest=planned['plan_digest'],
                 article_count=len(item['changes']),status=item['status'],questions=item['questions'],
                 approved=False,published=False,new_execution_started=False,
                 note='Source-derived drafts for review. An unapproved patch is not verified publication.')
    write_new(root/'receipt.json',receipt)
    report='# Documentation changes ready for review\n\n'
    report+=f"Project: {manifest['repository']}\n\nSource: {event.get('source_url',event['id'])}\n\n"
    report+=f"Base: `{planned['base_sha']}`\n\nHead: `{planned['head_sha']}`\n\n"
    report+='## Proposed articles\n\n'+''.join(f"- [{c['path']}](drafts/{c['path']}) — {c['reason']}\n" for c in item['changes'])
    report+='\n## Required before approved delivery\n\n'+''.join('- '+q+'\n' for q in item['questions'])
    report+='\nReview each article and record editor approval. The patch is a draft; no test pass, merge or publication is implied.\n'
    report+='\nInspect `receipt.json`, `event.json` and `changes.patch`. Use `cqa-docs-loop --db PATH/review.db --project '+project+' state` for the local review state. No web server or PostgreSQL is required.\n'
    (root/'REVIEW.md').write_text(report)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('plan');c.add_argument('--repo',type=Path,default=Path('.'));c.add_argument('--config',type=Path,default=Path('.docs-agent.json'));c.add_argument('--base',required=True);c.add_argument('--head',required=True);c.add_argument('--source-url');c.add_argument('--out',type=Path,required=True)
    c=sub.add_parser('validate');c.add_argument('--plan',type=Path,required=True);c.add_argument('--proposal',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
    c=sub.add_parser('prepare');c.add_argument('--plan',type=Path,required=True);c.add_argument('--proposal',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
    c=sub.add_parser('submit');c.add_argument('--event',type=Path,required=True);c.add_argument('--url',required=True);c.add_argument('--organization',required=True);c.add_argument('--project',required=True)
    c=sub.add_parser('intake',help='Forward a push or merged-PR payload through the signed GitHub intake path')
    c.add_argument('--payload',type=Path,required=True);c.add_argument('--url',required=True)
    c.add_argument('--organization',required=True);c.add_argument('--project',required=True)
    c.add_argument('--kind',choices=['push','pull_request'],required=True);c.add_argument('--delivery',required=True)
    args=p.parse_args()
    if args.command=='plan':
        result=plan(args.repo,json.loads(args.config.read_text()),args.base,args.head,args.source_url);write_new(args.out,result)
        print(json.dumps({'plan':str(args.out),'affected_articles':len(result['articles']),'executed':False}))
    elif args.command=='prepare':
        print(json.dumps(prepare(json.loads(args.plan.read_text()),json.loads(args.proposal.read_text()),args.out),indent=2))
    elif args.command=='validate':
        result=validate_proposal(json.loads(args.plan.read_text()),json.loads(args.proposal.read_text()));write_new(args.out,result)
        print(json.dumps({'event':str(args.out),'edits':len(result['edits']),'review_required':True}))
    elif args.command=='intake':
        with args.payload.open('rb') as f:payload=f.read(2*1024*1024+1)
        print(json.dumps(intake(payload,args.url,args.organization,args.project,args.kind,args.delivery,os.getenv('DOCS_WEBHOOK_SECRET'))))
    else:print(json.dumps(submit(json.loads(args.event.read_text()),args.url,args.organization,args.project,os.environ.get('DOCS_AGENT_TOKEN',''))))

def cli():
    try:main()
    except (Rejected,ValueError,OSError,subprocess.TimeoutExpired) as e:
        print(str(e),file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':cli()
