"""Repository-owned journey orchestration over saved ContextQA tests.

No background service. Definitions stay in ContextQA; mappings and expected
configuration are versioned in Git. All remote writes and runs are explicit.
"""
import argparse
import copy
import fnmatch
import json
import os
from pathlib import Path
import posixpath
import re
import sys

from . import agent, core
from .changes import reviewed
from .contextqa import (ContextQAClient, OPERATIONS, CONTRACT, positive_id, validate,
                        exclusive_json, replace_private_json, collect_results,
                        import_result_steps, now, journal_event)
from .loop import fingerprint, Store, text, strings
from .project import validate_project, inspect_project, matches


def sealed(value, key='digest'):
    result=copy.deepcopy(value);result[key]=fingerprint(value);return result


def checked(value, key='digest'):
    result=copy.deepcopy(value);digest=result.pop(key,None)
    if digest!=fingerprint(result):raise core.Rejected('Integrity check failed; regenerate the input')
    return result


def registry(value):
    if not isinstance(value,dict) or set(value)!={'schema','repository','journeys'} or value['schema']!=1:
        raise core.Rejected('Journey registry needs schema, repository and journeys')
    text(value['repository'],'repository',200)
    rows=value['journeys']
    if not isinstance(rows,list) or not 1<=len(rows)<=100:raise core.Rejected('Use 1–100 journeys')
    seen=set()
    for row in rows:
        required={'id','name','sections','code_paths','application_url','environment','workspace_version_id','profile','case_ids','required_media'}
        if not isinstance(row,dict) or set(row)-{'definition_locks'}!=required:raise core.Rejected('Invalid journey fields')
        ident=row['id']
        if not isinstance(ident,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',ident) or ident in seen:
            raise core.Rejected('Journey IDs must be unique safe slugs')
        seen.add(ident)
        for key in ('name','application_url','environment'):text(row[key],key,500)
        from urllib.parse import urlsplit
        url=urlsplit(row['application_url'])
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise core.Rejected('Journey application must be credential-free HTTPS')
        positive_id(row['workspace_version_id']);validate_project(row['profile'])
        for key in ('sections','code_paths'):
            if not strings(row[key],key):raise core.Rejected('Journey mappings cannot be empty')
        ids=row['case_ids']
        if not isinstance(ids,list) or not 1<=len(ids)<=100 or len(ids)!=len(set(ids)):
            raise core.Rejected('Journey needs unique case IDs')
        for ident in ids:positive_id(ident)
        cases={r['id']:r for r in row['profile'].get('cases',[])}
        if not set(ids)<=set(cases):raise core.Rejected('Every selected case needs an expected configuration')
        if any(cases[i]['expect'].get('workspaceVersionId')!=row['workspace_version_id'] for i in ids):
            raise core.Rejected('Expected cases must bind the journey workspace')
        if not isinstance(row['required_media'],list) or any(k not in ('screenshot','video') for k in row['required_media']):
            raise core.Rejected('Unknown journey media requirement')
        locks=row.get('definition_locks',{})
        allowed={'case:'+str(r['id']) for r in row['profile'].get('cases',[])}|{'step:'+str(r['id']) for r in row['profile'].get('steps',[])}
        if not isinstance(locks,dict) or any(k not in allowed or not re.fullmatch(r'[a-f0-9]{64}',str(v)) for k,v in locks.items()):
            raise core.Rejected('Invalid journey definition locks')
    return copy.deepcopy(value)


def select(value,ident):
    value=registry(value)
    result=next((r for r in value['journeys'] if r['id']==ident),None)
    if result is None:raise core.Rejected('Unknown journey ID')
    return result


def impact(planned,value):
    checked(planned,'plan_digest');value=registry(value)
    if value['repository']!=planned['manifest']['repository']:raise core.Rejected('Journey repository mismatch')
    section_ids={s['id'] for s in planned['manifest']['sections']}
    if any(not set(j['sections'])<=section_ids for j in value['journeys']):raise core.Rejected('Unknown documentation section in journey mapping')
    affected=set(planned['affected_sections']);paths=planned['event']['changed_paths']
    selected=[j for j in value['journeys'] if affected.intersection(j['sections']) or any(fnmatch.fnmatchcase(p,g) for p in paths for g in j['code_paths'])]
    covered={s for j in selected for s in j['sections']}
    return sealed(dict(schema=1,registry_digest=fingerprint(value),plan_digest=planned['plan_digest'],
                       head_sha=planned['head_sha'],journeys=selected,
                       unmapped_sections=sorted(affected-covered),executed=False))


def page_all(client,operation,query,parent_key,parent_id):
    rows=[];seen=set()
    for page in range(3):
        response=client.call(operation,query={'query':query,'page':page,'size':100,'sort':'id,asc'})
        batch=response.get('content') if isinstance(response,dict) else response
        if not isinstance(batch,list):raise core.Rejected('Unexpected paginated result shape')
        for row in batch:
            if not isinstance(row,dict) or row.get(parent_key)!=parent_id or type(row.get(parent_key)) is not int:
                raise core.Rejected('Result filter failed parent membership validation')
            ident=positive_id(row.get('id'))
            if ident in seen:raise core.Rejected('Repeated result across pages; selection is ambiguous')
            seen.add(ident);rows.append(row)
        if isinstance(response,dict) and response.get('last') is True or len(batch)<100:return rows
    raise core.Rejected('Result selection exceeds three pages; narrow the saved plan')


def inspect(client,journey):
    result=inspect_project(client,journey['profile'])
    for kind,(_,write,group) in RESOURCE_OPS.items():
        for actual in result['observed'][group]:
            expected=journey.get('definition_locks',{}).get(kind+':'+str(actual['id']))
            if expected and definition_digest(write,actual)!=expected:
                raise core.Rejected('Journey definition changed; review maintenance before capture or execution')
    return result


def register(client,value,ident):
    """Adopt existing saved cases and snapshot their step definitions as hashes.

    Raw selectors/test data stay in ContextQA and private preflight records;
    the portable registry contains identifiers and definition hashes only.
    """
    value=registry(value);journey=select(value,ident)
    observed=inspect_project(client,journey['profile'])['observed']
    definitions=[]
    for case in observed['cases']:
        rows=page_all(client,'listTestSteps',f"testCaseId:{case['id']}",'testCaseId',case['id'])
        for row in rows:
            # List DTOs can omit fields present in detail DTOs. Lock the same
            # detail representation that subsequent preflight checks will read.
            detail=client.call('getTestStep',id=row['id'])
            if detail.get('id')!=row['id'] or detail.get('testCaseId')!=case['id']:
                raise core.Rejected('Step detail does not match the registered case')
            definitions.append(detail)
    if len(definitions)>100:raise core.Rejected('Registered journey exceeds 100 definition steps')
    journey['profile']['steps']=[{'id':s['id'],'expect':{'testCaseId':s['testCaseId']}} for s in definitions]
    journey['definition_locks']={
        **{'case:'+str(c['id']):definition_digest('updateTestCase',c) for c in observed['cases']},
        **{'step:'+str(s['id']):definition_digest('updateTestStep',s) for s in definitions}}
    value['journeys']=[journey if r['id']==ident else r for r in value['journeys']]
    return registry(value)


def deployment_check(value,journey,run_id,head):
    if not isinstance(value,dict):return False
    required={'run_id','commit_sha','application_url','environment','journey_digest','verified_by','evidence_ref','confirmed'}
    if set(value)!=required or value['confirmed'] is not True:return False
    return (type(value['run_id']) is int and value['run_id']==run_id and value['commit_sha']==head
            and value['application_url']==journey['application_url'] and value['environment']==journey['environment']
            and value['journey_digest']==fingerprint(journey)
            and all(isinstance(value[k],str) and 0<len(value[k])<=1000 for k in ('verified_by','evidence_ref')))


def capture(client,value,ident,run_id,head,out,deployment=None):
    value=registry(value);journey=select(value,ident);positive_id(run_id)
    if not re.fullmatch(r'[a-f0-9]{40}',head):raise core.Rejected('Capture requires a full commit SHA')
    out=Path(out)
    if out.exists():raise core.Rejected('Capture output must be new; preserve previous evidence')
    preflight=inspect(client,journey)
    run=client.call('getTestPlanResult',id=run_id)
    if run.get('id')!=run_id or run.get('testPlanId')!=journey['profile']['plan']['id']:
        raise core.Rejected('Run belongs to a different saved plan')
    all_cases=page_all(client,'listTestCaseResults',f'testPlanResultId:{run_id}','testPlanResultId',run_id)
    cases=[r for r in all_cases if r.get('testCaseId') in journey['case_ids']]
    if sorted(r.get('testCaseId') for r in cases)!=sorted(journey['case_ids']):
        raise core.Rejected('Missing or multiple results for a mapped case; select an unambiguous run')
    steps=[]
    for case in cases:
        batch=page_all(client,'listTestStepResults',f"testCaseResultId:{case['id']}",'testCaseResultId',case['id'])
        # Never let partial step pagination or duplicate executions count as full evidence.
        count=case.get('totalCount')
        if type(count) is not int or count<0 or len(batch)!=count:
            raise core.Rejected('Returned steps do not match the case step count')
        if any(r.get('testCaseId') not in (None,case['testCaseId']) for r in batch):
            raise core.Rejected('Step belongs to a different mapped case')
        # API result position, not result ID, determines execution order when available.
        batch.sort(key=lambda r:(r.get('position') if type(r.get('position')) is int else r['id'],r['id']))
        steps.extend(batch)
    if len(steps)>100:raise core.Rejected('Journey exceeds the 100 selected-step evidence limit')
    core.init(out,journey['name'])
    receipt=collect_results(client,out,run_id,[r['id'] for r in cases],[r['id'] for r in steps],plan_id=journey['profile']['plan']['id'])
    if steps:import_result_steps(out)
    core.set_context(out,dict(workflow_id=ident,commit_sha=head,environment=journey['environment'],capture_method='ContextQA saved journey'))
    refs=core.load_json(out/'private/artifact-references.json')
    inventory=[{'index':i,'record':r['record'],'field':r['field']} for i,r in enumerate(refs)]
    verified=deployment_check(deployment,journey,run_id,head)
    record=sealed(dict(schema=1,journey=journey,registry_digest=fingerprint(value),head_sha=head,run_id=run_id,
        collected_at=now(),receipt=receipt,deployment=deployment,deployment_verified=verified,
        preflight_digest=preflight['observedSha256'],source_sha256=core.export_digest(core.load_json(out/'private/contextqa-results.json')),
        artifact_inventory=inventory,review_required=True))
    exclusive_json(out/'journey-capture.json',record)
    exclusive_json(out/'private/preflight.json',preflight)
    return dict(capture=str(out),journey=ident,verdict=receipt['verdict'],steps=len(steps),
                artifact_references=len(refs),deployment_verified=verified,review_required=True,new_execution_started=False)


def run(client,value,ident,out,approve_execution=False):
    journey=select(value,ident);out=Path(out)
    if out.exists():raise core.Rejected('Use a new execution directory; resume existing runs by ID')
    if not approve_execution:raise core.Rejected('Execution requires explicit approval of the saved plan and its cost')
    preflight=inspect(client,journey)
    exclusive_json(out/'preflight.json',preflight)
    accepted=client.trigger_run(journey['profile']['plan']['id'],out/'run.jsonl',approve_execution=True,
        environment=journey['profile'].get('execution',{}).get('query',{}).get('environment'),preflight=preflight)
    exclusive_json(out/'accepted.json',accepted)
    options=journey['profile'].get('execution',{})
    result=client.poll_run(accepted['run_id'],max_attempts=options.get('maxPolls',20),interval=options.get('intervalMs',2000)/1000,deadline=60)
    exclusive_json(out/'poll.json',result)
    return result


def collect(client,planned,value,runs,out):
    """Collect every impacted journey from CI-supplied accepted run IDs."""
    report=impact(planned,value)
    if report['unmapped_sections']:raise core.Rejected('Map all affected sections before collecting a documentation refresh')
    ids={r['id'] for r in report['journeys']}
    if not isinstance(runs,dict) or set(runs)!=ids:raise core.Rejected('Provide the exact impacted journey run map')
    for spec in runs.values():
        if not isinstance(spec,dict) or set(spec)-{'deployment'}!={'run_id'}:raise core.Rejected('Run map entries need run_id and optional deployment attestation')
        positive_id(spec['run_id'])
    out=Path(out)
    if out.exists():raise core.Rejected('Use a new collection directory')
    exclusive_json(out/'impact.json',report)
    receipts=[]
    for ident,spec in runs.items():
        receipt=capture(client,value,ident,spec['run_id'],planned['head_sha'],out/ident,spec.get('deployment'))
        receipts.append(receipt)
        replace_private_json(out/'collection.json',dict(journeys=receipts,new_execution_started=False,review_required=True))
    return dict(journeys=receipts,new_execution_started=False,review_required=True)


RESOURCE_OPS={'case':('getTestCase','updateTestCase','cases'),'step':('getTestStep','updateTestStep','steps')}


def writable(operation,actual):
    def project(value,schema):
        if '$ref' in schema:schema=CONTRACT['schemas'][schema['$ref'].split('/')[-1]]
        if isinstance(value,dict) and schema.get('properties'):
            props=schema['properties'];result={}
            for k,v in value.items():
                if k not in props:continue
                child=props[k]
                resolved=CONTRACT['schemas'][child['$ref'].split('/')[-1]] if '$ref' in child else child
                if v is None and not resolved.get('nullable') and k not in schema.get('required',[]):continue
                result[k]=project(v,child)
            return result
        if isinstance(value,list) and 'items' in schema:return [project(v,schema['items']) for v in value]
        return copy.deepcopy(value)
    # Read DTOs emit null in optional nested fields whose write schema excludes
    # null. Project recursively; retain every documented non-null write value.
    return project(actual,OPERATIONS[operation]['body'])


def definition_digest(operation,actual):
    from urllib.parse import urlsplit, urlunsplit
    value=copy.deepcopy(writable(operation,actual))
    # ContextQA re-signs this media reference on reads. Its signature/expiry is
    # not a test-definition edit. Keep the underlying artifact path in the lock.
    reference=value.get('goldenScreenshot')
    if isinstance(reference,str) and reference.startswith('https://'):
        u=urlsplit(reference);value['goldenScreenshot']=urlunsplit((u.scheme,u.netloc,u.path,'',''))
    return fingerprint(value)


def maintenance_plan(client,value,ident,changes):
    journey=select(value,ident)
    if not isinstance(changes,list) or not 1<=len(changes)<=100:raise core.Rejected('Provide 1–100 reviewed resource changes')
    inspect(client,journey);updates=[];seen=set()
    for change in changes:
        if not isinstance(change,dict) or set(change)!={'kind','id','changes','reason'} or change['kind'] not in RESOURCE_OPS:
            raise core.Rejected('Updates need kind, id, changes and reason')
        kind=change['kind'];ident=positive_id(change['id']);read,write,group=RESOURCE_OPS[kind]
        if ident not in {r['id'] for r in journey['profile'].get(group,[])} or (kind,ident) in seen:
            raise core.Rejected('Update must target one unique registered resource')
        seen.add((kind,ident));text(change['reason'],'reason',2000)
        patch=change['changes']
        if not isinstance(patch,dict) or not patch or set(patch)&{'id','workspaceVersionId','testCaseId','createdBy','deleted'}:
            raise core.Rejected('Cannot change resource identity or ownership')
        before=client.call(read,id=ident);body=writable(write,before)
        body.update(patch);validate(body,OPERATIONS[write]['body'])
        updates.append(dict(kind=kind,id=ident,operation=write,before_digest=definition_digest(write,before),body=body,changes=patch,reason=change['reason']))
    return sealed(dict(schema=1,journey_id=journey['id'],journey_digest=fingerprint(journey),registry_digest=fingerprint(registry(value)),updates=updates))


def apply_maintenance(client,value,planned,out,approve_write=False):
    checked(planned);journey=select(value,planned['journey_id'])
    if planned['registry_digest']!=fingerprint(registry(value)) or planned['journey_digest']!=fingerprint(journey):
        raise core.Rejected('Registry changed; regenerate maintenance plan')
    if not approve_write:raise core.Rejected('Review the maintenance plan and explicitly approve writes')
    out=Path(out)
    if out.exists():raise core.Rejected('Maintenance receipt already exists; reconcile before retrying')
    # Recheck all resources before first write. The server has no conditional PUT;
    # use a controlled authoring window and verify every response afterwards.
    for change in planned['updates']:
        read,write,_=RESOURCE_OPS[change['kind']]
        group=RESOURCE_OPS[change['kind']][2]
        if change['id'] not in {r['id'] for r in journey['profile'].get(group,[])} or change['operation']!=write:
            raise core.Rejected('Maintenance resource is not registered')
        validate(change['body'],OPERATIONS[write]['body'])
        actual=client.call(read,id=change['id'])
        if definition_digest(write,actual)!=change['before_digest']:raise core.Rejected('Remote definition drift; no changes applied')
    exclusive_json(out/'plan.json',planned)
    updated=copy.deepcopy(value)
    target=next(j for j in updated['journeys'] if j['id']==journey['id'])
    for n,change in enumerate(planned['updates']):
        read,write,group=RESOURCE_OPS[change['kind']]
        # Intent exists before each non-idempotent request; failure leaves it for reconciliation.
        client.call_to_file(write,out/f'write-{n}.json',id=change['id'],body=change['body'],approve_write=True)
        actual=client.call(read,id=change['id'])
        if not matches(change['changes'],actual):raise core.Rejected('Write did not verify; reconcile the saved receipt')
        row=next(r for r in target['profile'][group] if r['id']==change['id'])
        row['expect'].update(change['changes'])
        if target.get('definition_locks'):
            target['definition_locks'][change['kind']+':'+str(change['id'])]=definition_digest(write,actual)
    exclusive_json(out/'registry.next.json',registry(updated))
    exclusive_json(out/'receipt.json',dict(completed=True,writes=len(planned['updates']),new_execution_started=False))
    return dict(completed=True,writes=len(planned['updates']),registry=str(out/'registry.next.json'),new_execution_started=False)


def review_capture(root,recipe,out,reviewer,confirmed=False):
    root=Path(root);out=Path(out);record=core.load_json(root/'journey-capture.json');checked(record)
    if out.exists():raise core.Rejected('Choose a new reviewed export directory')
    if not confirmed:raise core.Rejected('Explicit content, media and rights review is required')
    if record['receipt']['verdict']!='passed' or not record['deployment_verified']:
        raise core.Rejected('Passing journey and reviewed deployment attestation required')
    if core.export_digest(core.load_json(root/'private/contextqa-results.json'))!=record['source_sha256']:
        raise core.Rejected('Collected results changed since capture')
    data=core.manifest(root)
    execution=data.get('execution',{})
    if (execution.get('source_sha256')!=record['source_sha256'] or execution.get('run_id')!=record['run_id']
        or execution.get('verdict')!='passed' or data.get('capture_context',{}).get('workflow_id')!=record['journey']['id']
        or data.get('capture_context',{}).get('commit_sha')!=record['head_sha']):
        raise core.Rejected('Capture provenance changed before review')
    if not isinstance(recipe,dict) or set(recipe)!={'steps'} or not isinstance(recipe['steps'],list):raise core.Rejected('Review recipe needs explicit steps')
    if len(recipe['steps'])!=len(data['steps']):raise core.Rejected('Review every collected step')
    for n,(original,step) in enumerate(zip(data['steps'],recipe['steps']),1):
        if not isinstance(step,dict) or set(step)!={'step_result_id','title','instruction','media_ids'}:
            raise core.Rejected('Review step requires result ID, title, instruction and media IDs')
        if step['step_result_id']!=original['step_result_id']:raise core.Rejected('Review step/result mapping mismatch')
        text(step['title'],'title',500);text(step['instruction'],'instruction',10000)
        if not isinstance(step['media_ids'],list):raise core.Rejected('Invalid media selection')
        known={m['id'] for m in data['media']}
        if any(mid not in known for mid in step['media_ids']):raise core.Rejected('Unknown reviewed media ID')
    selected={mid for step in recipe['steps'] for mid in step['media_ids']}
    kinds={m['kind'] for m in data['media'] if m['id'] in selected}
    if not set(record['journey']['required_media'])<=kinds:raise core.Rejected('Required journey screenshot/video missing')
    # A replacement review is an exact selection, not an additive attachment.
    for step in data['steps']:step['media']=[]
    core.save(root,data)
    for n,step in enumerate(recipe['steps'],1):
        core.edit_step(root,n,step['title'],step['instruction'])
        for mid in step['media_ids']:core.attach(root,n,mid)
    core.approve(root,reviewer,True)
    core.export(root,out,'https://review.invalid')
    receipt=sealed(dict(schema=1,journey_id=record['journey']['id'],journey_digest=fingerprint(record['journey']),
        registry_digest=record['registry_digest'],head_sha=record['head_sha'],run_id=record['run_id'],
        source_sha256=record['source_sha256'],deployment=record['deployment'],
        export_digest=fingerprint(reviewed(out)),reviewed_by=reviewer))
    exclusive_json(out/'journey-review.json',receipt)
    return dict(export=str(out),steps=len(recipe['steps']),media=len(selected),review_required_for_documentation=True)


def fetch_capture_media(root,hosts,max_files=20):
    """Download selected journey media privately and propose step associations.

    The generated recipe still requires content review; downloading is not approval.
    """
    from urllib.parse import urlsplit
    from .media import fetch_media
    root=Path(root)
    if (root/'review-recipe.json').exists():raise core.Rejected('Media recipe already exists; use selected fetch-media for further downloads')
    if type(max_files) is not int or not 1<=max_files<=50:raise core.Rejected('Use a media limit of 1–50 files')
    if not isinstance(hosts,list) or not hosts:raise core.Rejected('Supply reviewed storage host names')
    refs=core.load_json(root/'private/artifact-references.json');data=core.manifest(root)
    selected=[]
    for i,ref in enumerate(refs):
        field=ref['field'].split('/')[0]
        kind='video' if field in ('screenRecordingUrl','screenRecordings') else 'screenshot' if field in ('screenShotURL','screenshotUrl','snapshotUrl','screenshots') else None
        if kind and urlsplit(ref['url']).hostname in hosts and ref['record'].split(':')[0] in ('cases','steps'):
            selected.append((i,ref,kind))
    if len(selected)>max_files:raise core.Rejected('Media exceeds the selected download limit; use individual fetch-media selections')
    recipe={'steps':[dict(step_result_id=s['step_result_id'],title=s['title'],instruction=s['instruction'],media_ids=[]) for s in data['steps']]}
    for i,ref,kind in selected:
        result=fetch_media(root,i,kind,urlsplit(ref['url']).hostname)
        group,ident=ref['record'].split(':');ident=int(ident)
        candidates=[n for n,s in enumerate(data['steps']) if s.get('step_result_id' if group=='steps' else 'case_result_id')==ident]
        # A case recording is linked once, at the first documented step of that case.
        for n in candidates[:1]:recipe['steps'][n]['media_ids'].append(result['media_id'])
    exclusive_json(root/'review-recipe.json',recipe)
    return dict(downloaded=len(selected),recipe=str(root/'review-recipe.json'),attached=False,review_required=True)


def evidence_plan(planned,value,exports):
    report=impact(planned,value)
    if report['unmapped_sections']:raise core.Rejected('Affected documentation has no journey mapping: '+', '.join(report['unmapped_sections']))
    if set(exports)!={j['id'] for j in report['journeys']}:raise core.Rejected('Provide exactly one reviewed export for every affected journey')
    result=copy.deepcopy(planned);result.pop('plan_digest');evidence=[];requirements=[]
    for journey in report['journeys']:
        root=Path(exports[journey['id']]);data=reviewed(root);receipt=core.load_json(root/'journey-review.json');checked(receipt)
        execution=data.get('execution',{})
        if (receipt['registry_digest']!=report['registry_digest'] or receipt['journey_digest']!=fingerprint(journey)
            or receipt['journey_id']!=journey['id'] or receipt['head_sha']!=planned['head_sha']
            or receipt['export_digest']!=fingerprint(data) or execution.get('source_sha256')!=receipt['source_sha256']
            or execution.get('run_id')!=receipt['run_id'] or execution.get('verdict')!='passed'
            or not deployment_check(receipt['deployment'],journey,receipt['run_id'],planned['head_sha'])):
            raise core.Rejected('Reviewed evidence is stale, unrelated, failed or changed')
        if execution.get('transport')=='simulated' and planned['manifest'].get('allow_simulated_evidence') is not True:
            raise core.Rejected('Simulated journey evidence is disabled')
        kinds={m['kind'] for m in data['media']}
        if not set(journey['required_media'])<=kinds:raise core.Rejected('Required reviewed media is missing')
        evidence.append(dict(journey_id=journey['id'],sections=journey['sections'],export_digest=fingerprint(data),capture=data))
        requirements.append(dict(journey_id=journey['id'],source_sha256=execution['source_sha256'],export_digest=fingerprint(data)))
    result['journey_evidence']=evidence;result['event']['journey_requirements']=requirements
    result['event']['requires_capture']=True
    result['event']['id']+=':journeys:'+fingerprint(requirements)[:16]
    if len(json.dumps(result).encode())>agent.MAX_CONTEXT:raise core.Rejected('Evidence context exceeds drafting limit; narrow the journey')
    return sealed(result,'plan_digest')


def draft_from_evidence(planned):
    checked(planned,'plan_digest');edits=[]
    for article in planned['articles']:
        section=next(s['id'] for s in planned['manifest']['sections'] if s['path']==article['path'])
        body=article['before'] or '# '+article['title']+'\n'
        for evidence in planned.get('journey_evidence',[]):
            if section not in evidence['sections']:continue
            ident=evidence['journey_id'];capture=evidence['capture'];lines=['## '+core.markdown_plain(capture['title']),'']
            media={m['id']:m for m in capture['media']}
            prefix='evidence/'+evidence['export_digest']+'/'
            for n,step in enumerate(capture['steps'],1):
                lines.extend([f"{n}. **{core.markdown_plain(step['title'])}** — {core.markdown_plain(step['instruction'])}",''])
                for mid in step['media']:
                    m=media[mid];relative=posixpath.relpath(prefix+m['path'],posixpath.dirname(article['path']) or '.')
                    marker='!' if m['kind']=='screenshot' else ''
                    lines.extend([f"{marker}[{m['kind']} for step {n}]({relative})",''])
            start=f'<!-- contextqa:journey:{ident}:start -->';end=f'<!-- contextqa:journey:{ident}:end -->'
            block=start+'\n'+'\n'.join(lines)+'\n'+end
            if start in body or end in body:
                if body.count(start)!=1 or body.count(end)!=1 or body.index(start)>body.index(end):raise core.Rejected('Malformed managed journey block')
                body=body[:body.index(start)]+block+body[body.index(end)+len(end):]
            else:body=body.rstrip()+'\n\n'+block+'\n'
        if body!=article['before']:edits.append(dict(path=article['path'],after=body,reason='Refresh the mapped journey from reviewed ContextQA steps and media'))
    return dict(title='Refresh documented user journeys',summary='Review source changes alongside the observed journey instructions and media.',edits=edits,questions=[])


def prepare(planned,value,exports,out,proposal=None):
    enriched=evidence_plan(planned,value,exports)
    proposal=proposal if proposal is not None else draft_from_evidence(enriched)
    receipt=agent.prepare(enriched,proposal,out)
    store=Store(Path(out)/'review.db');project=enriched['manifest']['project_id']
    for ident,path in exports.items():
        item=store.snapshot(project,'owner')['items'][receipt['item_id']]
        store.attach_evidence(project,'owner',item['id'],item['version'],Path(path))
    # Copy reviewed evidence into the local draft tree so preview links resolve.
    import shutil
    for evidence in enriched['journey_evidence']:
        source=Path(exports[evidence['journey_id']]);target=Path(out)/'drafts/evidence'/evidence['export_digest']
        core.private_dir(target)
        for m in evidence['capture']['media']:
            destination=target/m['path'];core.private_dir(destination.parent)
            shutil.copyfile(core.asset_file(source,m['path']),destination);os.chmod(destination,0o600)
    exclusive_json(Path(out)/'journey-impact.json',impact(planned,value))
    return dict(receipt,journeys_attached=len(exports),review_required=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('register','impact','inspect','capture','collect','run','maintenance-plan','apply-maintenance','prepare','evidence-plan'):
        p=sub.add_parser(name);p.add_argument('--registry',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
        if name in ('impact','prepare','evidence-plan','collect'):p.add_argument('--plan',type=Path,required=True)
        else:p.add_argument('--journey',required=name!='apply-maintenance')
        if name in ('prepare','evidence-plan'):p.add_argument('--exports',type=Path,required=True)
        if name=='prepare':p.add_argument('--proposal',type=Path)
        if name=='capture':
            p.add_argument('--run-id',type=int,required=True);p.add_argument('--head',required=True);p.add_argument('--deployment',type=Path)
        if name=='run':p.add_argument('--approve-execution',action='store_true')
        if name=='collect':p.add_argument('--runs',type=Path,required=True)
        if name=='maintenance-plan':p.add_argument('--changes',type=Path,required=True)
        if name=='apply-maintenance':p.add_argument('--maintenance',type=Path,required=True);p.add_argument('--approve-write',action='store_true')
    p=sub.add_parser('review');p.add_argument('--capture',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--reviewer',required=True);p.add_argument('--confirm-content-and-rights',action='store_true')
    p=sub.add_parser('media');p.add_argument('--capture',type=Path,required=True);p.add_argument('--allow-host',action='append',required=True);p.add_argument('--max-files',type=int,default=20)
    a=parser.parse_args();read=lambda p:core.load_json(p)
    value=registry(read(a.registry)) if hasattr(a,'registry') else None
    if a.command in ('register','inspect','capture','collect','run','maintenance-plan','apply-maintenance'):client=ContextQAClient(os.environ.get('CONTEXTQA_API_TOKEN'))
    if a.command=='impact':result=impact(read(a.plan),value);exclusive_json(a.out,result)
    elif a.command=='inspect':
        result=inspect(client,select(value,a.journey));exclusive_json(a.out,result);result={'checked':True,'saved_privately':str(a.out)}
    elif a.command=='register':
        result=register(client,value,a.journey);exclusive_json(a.out,result);result={'registry':str(a.out),'remote_writes':False}
    elif a.command=='capture':result=capture(client,value,a.journey,a.run_id,a.head,a.out,read(a.deployment) if a.deployment else None)
    elif a.command=='collect':result=collect(client,read(a.plan),value,read(a.runs),a.out)
    elif a.command=='run':result=run(client,value,a.journey,a.out,a.approve_execution)
    elif a.command=='maintenance-plan':
        result=maintenance_plan(client,value,a.journey,read(a.changes));exclusive_json(a.out,result);result={'maintenance_plan':str(a.out),'writes_started':False}
    elif a.command=='apply-maintenance':result=apply_maintenance(client,value,read(a.maintenance),a.out,a.approve_write)
    elif a.command=='review':result=review_capture(a.capture,read(a.recipe),a.out,a.reviewer,a.confirm_content_and_rights)
    elif a.command=='media':result=fetch_capture_media(a.capture,a.allow_host,a.max_files)
    elif a.command=='evidence-plan':
        result=evidence_plan(read(a.plan),value,read(a.exports));exclusive_json(a.out,result);result={'plan':str(a.out),'reviewed_journeys':len(result['journey_evidence'])}
    else:result=prepare(read(a.plan),value,read(a.exports),a.out,read(a.proposal) if a.proposal else None)
    print(json.dumps(result,indent=2))


def cli():
    try:main()
    except core.Rejected as error:
        print(str(error),file=sys.stderr)
        raise SystemExit(1)
    except (OSError,ValueError,KeyError,TypeError):
        # Inputs may contain private API data. Do not echo arbitrary values/errors.
        print('Journey operation rejected. Check mappings, evidence, configuration drift and private receipts; no automatic retry.',file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':cli()
