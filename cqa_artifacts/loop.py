"""Durable local documentation loop. No network, execution or automatic publication."""
import base64
import copy
import difflib
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager, closing
from .core import Rejected


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def text(value, label, limit=100000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\0' in value:
        raise Rejected('Invalid ' + label)
    return value


def path_name(value):
    text(value, 'document path', 250)
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or p.suffix not in ('.md', '.mdx') or value.startswith('.'):
        raise Rejected('Use a relative Markdown document path')
    return value


LIST_LIMIT = 200
LIST_ITEM_LIMIT = 500


def strings(value, label):
    """Bounded string lists; the agent applies the same limits before submission."""
    if not isinstance(value, list) or len(value) > LIST_LIMIT:
        raise Rejected('Invalid ' + label)
    return [text(v, label, LIST_ITEM_LIMIT) for v in value]


def validate_manifest(value):
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise Rejected('Documentation manifest needs schema 1')
    for key in ('project_id', 'name', 'repository', 'application_url', 'environment', 'instructions'):
        text(value.get(key), key)
    sections = value.get('sections')
    if not isinstance(sections, list) or not 1 <= len(sections) <= 200:
        raise Rejected('Manifest needs 1–200 sections')
    ids, paths = set(), set()
    for row in sections:
        if not isinstance(row, dict):
            raise Rejected('Invalid section')
        for key in ('id', 'title', 'owner'):
            text(row.get(key), key, 200)
        path_name(row.get('path'))
        if row['id'] in ids or row['path'] in paths:
            raise Rejected('Section IDs and paths must be unique')
        ids.add(row['id']); paths.add(row['path'])
        strings(row.get('code_paths', []), 'code_paths')
        strings(row.get('module_ids', []), 'module_ids')
        strings(row.get('keywords', []), 'keywords')
    return copy.deepcopy(value)


class Store:
    """One operator-owned SQLite file; all mutations use serialized transactions.

    Members/roles enforce local workflow policy, not remote authentication. Server
    credentials select a fixed member; request bodies cannot supply an actor.
    """
    def __init__(self, filename):
        self.filename = Path(filename)
        if self.filename.is_symlink():
            raise Rejected('Database must not be a symlink')
        self.filename.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.filename.exists():
            fd = os.open(self.filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        os.chmod(self.filename, 0o600)
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT NOT NULL)')

    def connect(self):
        db = sqlite3.connect(self.filename, timeout=10)
        db.execute('PRAGMA foreign_keys=ON')
        return db

    @contextmanager
    def transaction(self, project):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM projects WHERE id=?', (project,)).fetchone()
            if not row:
                raise Rejected('Unknown project')
            state = json.loads(row[0])
            yield state
            db.execute('UPDATE projects SET data=? WHERE id=?', (encoded(state), project))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, manifest, owner='owner'):
        manifest = validate_manifest(manifest)
        text(owner, 'owner', 200)
        state = dict(manifest=manifest, members={owner:'admin'}, articles={}, events={}, items={}, audit=[])
        with closing(self.connect()) as db, db:
            try:
                db.execute('INSERT INTO projects VALUES (?,?)', (manifest['project_id'], encoded(state)))
            except sqlite3.IntegrityError:
                raise Rejected('Project already exists') from None
        return manifest['project_id']

    @staticmethod
    def authorize(s, actor, roles=('admin', 'editor'), item=None):
        role = s['members'].get(actor)
        if role in roles and role != 'contributor':
            return
        if role == 'contributor' and 'contributor' in roles and item is None:
            return
        if item and role == 'contributor' and item.get('assignee') == actor and 'contributor' in roles:
            return
        raise Rejected('This member cannot perform that action')

    @staticmethod
    def log(s, actor, action, item=None):
        s['audit'].append(dict(at=time.time(), actor=actor, action=action, item=item))

    @staticmethod
    def get_item(s, item_id):
        if item_id not in s['items']:
            raise Rejected('Unknown inbox item')
        return s['items'][item_id]

    def snapshot(self, project, actor):
        with self.transaction(project) as s:
            self.authorize(s, actor, ('admin','editor','contributor'))
            result = copy.deepcopy(s)
            if s['members'][actor] == 'contributor':
                result['items'] = {k:v for k,v in result['items'].items() if v.get('assignee') == actor}
                result['events'] = {v['event_id']:result['events'][v['event_id']] for v in result['items'].values()}
                result['articles'] = {k:v for k,v in result['articles'].items() if any(c['path']==k for i in result['items'].values() for c in i['changes'])}
                result['audit'] = [a for a in result['audit'] if a['item'] in result['items']]
            result['actor'] = actor
            result['role'] = s['members'][actor]
            return result

    def member(self, project, actor, name, role):
        text(name, 'member', 200)
        if role not in ('admin','editor','contributor'):
            raise Rejected('Invalid role')
        with self.transaction(project) as s:
            self.authorize(s, actor, ('admin',))
            if name == actor and role != 'admin':
                raise Rejected('Cannot demote current admin')
            s['members'][name] = role
            self.log(s, actor, 'member:'+role)

    def article(self, project, actor, path, title, body, expected=None):
        path_name(path); text(title, 'title', 250); text(body, 'article')
        with self.transaction(project) as s:
            self.authorize(s, actor)
            old = s['articles'].get(path)
            if old and expected != old['digest']:
                raise Rejected('Article changed; reload before saving')
            s['articles'][path] = dict(path=path, title=title, body=body, digest=fingerprint(body), updated_at=time.time())
            self.log(s, actor, 'article:save:'+path)
            return s['articles'][path]

    def ingest(self, project, actor, event):
        if not isinstance(event, dict):
            raise Rejected('Event must be an object')
        event = copy.deepcopy(event)
        for key in ('id','source','title','text'):
            text(event.get(key), 'event '+key)
        if event['source'] not in ('manual','github','linear','jira','slack','video','audit'):
            raise Rejected('Unsupported normalized source')
        strings(event.get('changed_paths', []), 'changed_paths')
        strings(event.get('module_ids', []), 'module_ids')
        requirements=event.get('journey_requirements',[])
        if not isinstance(requirements,list) or len(requirements)>100:
            raise Rejected('Invalid journey evidence requirements')
        seen_journeys=set()
        for requirement in requirements:
            if not isinstance(requirement,dict) or set(requirement)!={'journey_id','source_sha256','export_digest'}:
                raise Rejected('Invalid journey evidence requirement')
            ident=text(requirement['journey_id'],'journey ID',80)
            if ident in seen_journeys or any(not re.fullmatch(r'[a-f0-9]{64}',str(requirement[k])) for k in ('source_sha256','export_digest')):
                raise Rejected('Invalid or duplicate journey evidence requirement')
            seen_journeys.add(ident)
        if event.get('source_url'):
            from urllib.parse import urlsplit
            u = urlsplit(event['source_url'])
            if u.scheme != 'https' or not u.hostname or u.username or u.password:
                raise Rejected('Source URL must be credential-free HTTPS')
        edits = event.get('edits', [])
        if not isinstance(edits, list) or len(edits) > 200:
            raise Rejected('Too many edits')
        for edit in edits:
            if not isinstance(edit, dict):
                raise Rejected('Invalid edit')
            path_name(edit.get('path')); text(edit.get('after'), 'replacement')
            if not isinstance(edit.get('before'), str):
                raise Rejected('Edit needs exact before text (empty for a new page)')
            text(edit.get('reason'), 'reason', 2000)
        if len({e['path'] for e in edits}) != len(edits):
            raise Rejected('Use one complete replacement per article')
        digest = fingerprint(event)
        with self.transaction(project) as s:
            self.authorize(s, actor)
            previous = s['events'].get(event['id'])
            if previous:
                if previous['digest'] != digest:
                    raise Rejected('Event ID reused with different content')
                return dict(item_id=previous['item_id'], duplicate=True)
            if len(s['events']) >= 10000:
                raise Rejected('Local project event limit reached; archive the workspace')
            sections = s['manifest']['sections']
            corpus = (event['title']+' '+event['text']).lower()
            affected = []
            for section in sections:
                reasons = []
                if any(fnmatch.fnmatchcase(p, glob) for p in event.get('changed_paths',[]) for glob in section.get('code_paths',[])):
                    reasons.append('code path mapping')
                if set(event.get('module_ids',[])) & set(section.get('module_ids',[])):
                    reasons.append('module mapping')
                if any(k.lower() in corpus for k in section.get('keywords',[])):
                    reasons.append('keyword match (review relevance)')
                if any(e['path']==section['path'] for e in edits):
                    reasons.append('explicit article selection')
                if reasons:
                    affected.append(dict(id=section['id'], path=section['path'], owner=section['owner'], reasons=reasons))
            changes, questions = [], strings(event.get('agent_questions', []), 'agent_questions')
            for edit in edits:
                article = s['articles'].get(edit['path'])
                before = article['body'] if article else ''
                if before != edit['before']:
                    raise Rejected('Source article differs from exact before text: '+edit['path'])
                if before == edit['after']:
                    continue
                changes.append(dict(id=str(len(changes)+1), path=edit['path'], before=before, after=edit['after'],
                    base_digest=fingerprint(before), decision='pending', reason=edit['reason'], source=event.get('source_url', event['id']),
                    kind='update' if article else 'new', diff=''.join(difflib.unified_diff(before.splitlines(True), edit['after'].splitlines(True), fromfile='before/'+edit['path'], tofile='after/'+edit['path']))))
            changed = {c['path'] for c in changes}
            for a in affected:
                if a['path'] not in changed and not any(e['path']==a['path'] for e in edits):
                    questions.append('Supply supported replacement text or explain no change for '+a['path'])
            if not affected and not changes:
                questions.append('No section matches. Confirm coverage or add an article; no relevance is inferred.')
            if event.get('requires_capture') is True or event.get('requires_screenshots') is True:
                questions.append('Attach a reviewed ContextQA export for the changed workflow before delivery.')
            item_id = uuid.uuid4().hex[:16]
            item = dict(id=item_id,event_id=event['id'],title=event['title'],source=event['source'],status='needs_input' if questions else 'open' if changes else 'no_change',
                version=1,assignee=None,affected=affected,changes=changes,questions=questions,comments=[],evidence=[],created_at=time.time(),approval=None,delivery=None,
                instructions_digest=fingerprint(s['manifest']['instructions']))
            s['items'][item_id]=item
            s['events'][event['id']]=dict(digest=digest,event=event,item_id=item_id)
            self.log(s,actor,'event:ingest',item_id)
            return dict(item_id=item_id, duplicate=False)

    @staticmethod
    def editable(item, version):
        if type(version) is not int or item['version'] != version:
            raise Rejected('Review changed; reload before continuing')
        if item['status'] in ('delivered','resolved','archived'):
            raise Rejected('Delivered/resolved items are immutable; create a new event')

    def review(self, project, actor, item_id, version, action, **data):
        with self.transaction(project) as s:
            item = self.get_item(s,item_id)
            self.authorize(s,actor,('admin','editor','contributor'),item)
            if action=='restore':
                self.authorize(s,actor)
                if item['status']!='archived' or item['version']!=version:raise Rejected('Refresh the archived request before restoring it')
                item['status']=item.pop('previous_status','open')
                item['version']+=1
                self.log(s,actor,'review:restore',item_id)
                return copy.deepcopy(item)
            self.editable(item,version)
            if action in ('priority','archive','resolve','handoff','accept_item'):
                if action in ('priority','archive','resolve'): self.authorize(s,actor)
                if action=='priority':
                    if data.get('priority') not in ('normal','high','urgent'):raise Rejected('Choose a valid review priority')
                    item['priority']=data['priority']
                elif action=='accept_item':
                    if not any(c['decision']=='pending' for c in item['changes']):
                        raise Rejected('There are no pending articles in this request')
                    for change in item['changes']:
                        if change['decision']=='pending':change['decision']='accepted'
                    item['status']='needs_input' if item['questions'] else 'open'
                elif action=='handoff':
                    recipient=data.get('assignee')
                    if recipient in (actor,item.get('assignee')) or s['members'].get(recipient) not in ('editor','admin'):
                        raise Rejected('Choose a different editor or administrator to receive this handoff')
                    self.check_journeys(s,item)
                    if item['questions'] or not item['changes'] or any(c['decision']=='pending' for c in item['changes']) or item.get('writing',{}).get('status')=='in_progress':
                        raise Rejected('Complete the writing round and decide every change before handoff')
                    item['assignee']=recipient
                    item['status']='ready'
                    item.setdefault('handoffs',[]).append(dict(sender=actor,recipient=recipient,note=text(data.get('note'),'handoff note',2000),at=time.time(),channel='inbox'))
                else:
                    if action=='archive':item['previous_status']=item['status']
                    item['status']='archived' if action=='archive' else 'resolved'
            elif action == 'assign':
                self.authorize(s,actor)
                if data.get('assignee') not in s['members']:
                    raise Rejected('Choose an existing member')
                item['assignee']=data['assignee']
            elif action == 'comment':
                anchor=data.get('change_id')
                if anchor and not any(c['id']==anchor for c in item['changes']):raise Rejected('Choose an article in this request')
                item['comments'].append(dict(actor=actor,text=text(data.get('text'),'comment',10000),at=time.time(),change_id=anchor))
            elif action == 'answer':
                self.check_journeys(s,item)
                if any(s['events'][item['event_id']]['event'].get(k) for k in ('requires_capture','requires_screenshots')) and not item['evidence']:
                    raise Rejected('Reviewed capture evidence is required; a text answer cannot replace it')
                answer=text(data.get('text'),'answer',10000)
                item['comments'].append(dict(actor=actor,text=answer,at=time.time(),kind='answer',questions=item['questions']))
                item['questions']=[]
                item['status']='open' if item['changes'] else 'no_change'
            elif action=='reconcile':
                self.authorize(s,actor)
                change=next((c for c in item['changes'] if c['id']==data.get('change_id')),None)
                if not change:raise Rejected('Unknown article')
                target=path_name(data.get('path') or change['path'])
                if any(c is not change and c['path']==target for c in item['changes']):raise Rejected('A proposal already exists for that path')
                before=s['articles'].get(target,{}).get('body','')
                if (s['articles'][target]['digest'] if target in s['articles'] else None)!=data.get('base_digest'):raise Rejected('The article changed again. Refresh before resolving.')
                after=text(data.get('after'),'resolved draft')
                change.update(path=target,before=before,after=after,base_digest=fingerprint(before),decision='pending',kind='update' if before else 'new',
                              diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before/'+target,tofile='after/'+target)))
                item['status']='needs_input' if item['questions'] else 'open'
            elif action in ('accept','ignore','undo','edit'):
                change=next((c for c in item['changes'] if c['id']==data.get('change_id')),None)
                if not change:
                    raise Rejected('Unknown change')
                if action=='edit':
                    change['after']=text(data.get('after'),'draft')
                    change['diff']=''.join(difflib.unified_diff(change['before'].splitlines(True),change['after'].splitlines(True),fromfile='before/'+change['path'],tofile='after/'+change['path']))
                change['decision']={'accept':'accepted','ignore':'ignored'}.get(action,'pending')
            elif action == 'ready':
                self.check_journeys(s,item)
                if item.get('writing',{}).get('status')=='in_progress':raise Rejected('Submit the writing round first')
                if item['questions'] or any(c['decision']=='pending' for c in item['changes']):
                    raise Rejected('Answer questions and decide every change first')
                item['status']='ready'
            else:
                raise Rejected('Unknown review action')
            item['approval']=None
            if action in ('accept','ignore','undo','edit'):
                item['status']='needs_input' if item['questions'] else 'open'
            item['version']+=1
            self.log(s,actor,'review:'+action,item_id)
            if action=='handoff' and s['members'][actor]=='contributor':
                return dict(id=item_id,version=item['version'],assignee=item['assignee'],status=item['status'])
            return copy.deepcopy(item)

    def attach_evidence(self, project, actor, item_id, version, export_path):
        from .changes import reviewed
        root=Path(export_path)
        evidence=reviewed(root)
        # Existing export validation checks media bytes, review digest and step mapping.
        execution=evidence.get('execution')
        if execution and execution.get('verdict') != 'passed':
            raise Rejected('Failed or inconclusive capture cannot satisfy evidence requirement')
        if not execution:
            raise Rejected('Capture needs ContextQA execution provenance')
        with self.transaction(project) as s:
            self.authorize(s,actor)
            item=self.get_item(s,item_id); self.editable(item,version)
            event=s['events'][item['event_id']]['event']
            requirements=event.get('journey_requirements',[])
            if requirements and not any(
                r['journey_id']==evidence.get('capture_context',{}).get('workflow_id')
                and r['source_sha256']==execution.get('source_sha256')
                and r['export_digest']==fingerprint(evidence) for r in requirements):
                raise Rejected('Capture does not match an expected journey and reviewed evidence digest')
            if execution['transport']=='simulated' and s['manifest'].get('allow_simulated_evidence') is not True:
                raise Rejected('Simulated evidence is disabled for this project')
            if event.get('requires_screenshots') and not any(m['kind']=='screenshot' for m in evidence.get('media',[])):
                raise Rejected('This request requires an attached reviewed screenshot')
            expected=event.get('revision')
            if expected and evidence.get('capture_context',{}).get('commit_sha') != expected:
                raise Rejected('Capture version label must match the requested revision; deployment verification is separate')
            item['evidence'].append(dict(digest=fingerprint(evidence),execution=execution,media_count=len(evidence.get('media',[])),
                title=evidence['title'],export_path=str(root.resolve()),capture_context=evidence.get('capture_context',{})))
            item['approval']=None; item['version']+=1
            self.log(s,actor,'evidence:attach',item_id)
            return copy.deepcopy(item)

    @staticmethod
    def check_journeys(s,item):
        requirements=s['events'][item['event_id']]['event'].get('journey_requirements',[])
        for requirement in requirements:
            if not any(e['digest']==requirement['export_digest']
                       and e.get('capture_context',{}).get('workflow_id')==requirement['journey_id']
                       and e['execution'].get('source_sha256')==requirement['source_sha256'] for e in item['evidence']):
                raise Rejected('Every affected journey needs its own matching reviewed evidence')

    @staticmethod
    def approval_payload(s,item):
        return dict(**({'writing':item['writing']} if item.get('writing') else {}),changes=item['changes'],evidence=item['evidence'],instructions=fingerprint(s['manifest']['instructions']),
                    source=s['events'][item['event_id']]['digest'],comments=item['comments'])

    def approve(self, project, actor, item_id, version, confirmed=False):
        with self.transaction(project) as s:
            self.authorize(s,actor)
            item=self.get_item(s,item_id); self.editable(item,version)
            if confirmed is not True or item['status']!='ready':
                raise Rejected('Ready item and explicit content/rights review required')
            self.check_journeys(s,item)
            self.check_bases(s,item)
            from .editions import verify_article_links
            verify_article_links(item)
            self.check_generated_media(s,item)
            item['approval']=dict(actor=actor,digest=fingerprint(self.approval_payload(s,item)),at=time.time())
            item['version']+=1
            self.log(s,actor,'review:approve',item_id)
            return copy.deepcopy(item)

    @staticmethod
    def check_generated_media(s,item):
        event=s['events'][item['event_id']]['event']
        if item.get('writing',{}).get('status')=='drafted' or event.get('id','').startswith(('guide:','openapi:')):
            from .editions import checked_media
            checked_media(item,event)

    @staticmethod
    def check_bases(s,item):
        for c in item['changes']:
            if c['decision']=='accepted' and fingerprint(s['articles'].get(c['path'],{}).get('body',''))!=c['base_digest']:
                raise Rejected('Published baseline drift; create a fresh proposal against the current article')

    def bundle(self, project, actor, item_id):
        """Prepare immutable delivery bytes. Delivery is separate from publication."""
        with self.transaction(project) as s:
            self.authorize(s,actor)
            item=self.get_item(s,item_id)
            if item['status'] not in ('ready','delivered') or not item['approval'] or item['approval']['digest']!=fingerprint(self.approval_payload(s,item)):
                raise Rejected('Current hash-bound approval required')
            self.check_bases(s,item)
            accepted=[c for c in item['changes'] if c['decision']=='accepted']
            self.check_generated_media(s,item)
            self.check_journeys(s,item)
            if not accepted:
                raise Rejected('No accepted changes to deliver')
            evidence_files={}
            evidence_size=0
            for e in item['evidence']:
                from .changes import reviewed
                from . import core
                root=Path(e['export_path'])
                capture=reviewed(root)
                if fingerprint(capture)!=e['digest']:
                    raise Rejected('Capture evidence changed since review')
                prefix='evidence/'+e['digest']+'/'
                safe_files={'index.html':core.render(capture).encode(),
                    'manifest.json':encoded(capture).encode(),
                    'assets/contextqa-logo.svg':(Path(__file__).parent/'brand/contextqa-logo.svg').read_bytes()}
                for media in capture['media']:
                    safe_files[media['path']]=core.regular_file(core.asset_file(root,media['path']))
                for name,raw in safe_files.items():
                    evidence_size+=len(raw)
                    if evidence_size>16*1024*1024:
                        raise Rejected('Evidence exceeds local bundle limit of 16 MiB; deliver larger reviewed exports separately')
                    evidence_files[prefix+name]=base64.b64encode(raw).decode()
            result=dict(schema=1,project=project,item=item_id,files={c['path']:c['after'] for c in accepted},
                patch='\n'.join(c['diff'] for c in accepted),approval=item['approval'],source=s['events'][item['event_id']]['event'],
                evidence=[{k:v for k,v in e.items() if k!='export_path'} for e in item['evidence']],
                baseline={c['path']:c['base_digest'] for c in accepted},evidence_files=evidence_files,published=False,
                note='Reviewed local draft bundle. No external pull request or publication has occurred.')
            if item.get('writing',{}).get('destination'):
                result['source']={**result['source'],'documentation_destination':item['writing']['destination']}
            digest=fingerprint(result)
            if item.get('delivery',{} ) and item['delivery']['digest']==digest:return result
            item['delivery']=dict(digest=digest,at=time.time(),mode='local_draft_bundle')
            item['status']='delivered'; item['version']+=1
            self.log(s,actor,'delivery:bundle',item_id)
            return result

    def apply_local(self, project, actor, item_id, confirmed=False):
        """Explicitly update the local knowledge base; never a remote publication."""
        with self.transaction(project) as s:
            self.authorize(s,actor)
            item=self.get_item(s,item_id)
            self.check_generated_media(s,item)
            if confirmed is not True or item['status']!='delivered' or not item['delivery']:
                raise Rejected('Deliver and explicitly confirm local application first')
            self.check_bases(s,item)
            for c in item['changes']:
                if c['decision']=='accepted':
                    s['articles'][c['path']]=dict(path=c['path'],title=c['path'],body=c['after'],digest=fingerprint(c['after']),updated_at=time.time())
            item['status']='resolved'; item['version']+=1
            self.log(s,actor,'delivery:apply_local',item_id)
            return dict(resolved=True,published=False,destination='local_knowledge_base')

    def audit(self, project, actor, stale_days=30):
        if type(stale_days) is not int or not 1<=stale_days<=365:
            raise Rejected('stale_days must be 1–365')
        state=self.snapshot(project,actor)
        self.authorize(state,actor)
        issues=[]
        for path,a in state['articles'].items():
            if time.time()-a['updated_at'] > stale_days*86400:
                issues.append(dict(path=path,kind='stale',detail='Review article age'))
            for dest in re.findall(r'\]\(([^)]+)\)',a['body']):
                dest=dest.split('#')[0]
                if not dest or '://' in dest or dest.startswith(('mailto:', 'data:')):
                    continue
                import posixpath
                target=posixpath.normpath(posixpath.join(posixpath.dirname(path),dest))
                if dest.endswith('.md') and target not in state['articles']:
                    issues.append(dict(path=path,kind='broken_internal_link',detail=dest))
        for sec in state['manifest']['sections']:
            if sec['path'] not in state['articles']:
                issues.append(dict(path=sec['path'],kind='coverage_gap',detail=sec['id']))
        return dict(issues=issues,external_links_checked=False,semantic_contradictions_checked=False)
