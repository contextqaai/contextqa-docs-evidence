"""Resumable ContextQA-only documentation workflow for an agent or CI job.

Collect executes no tests: accepted run IDs are explicit inputs. Finalize requires
reviewed editorial content and atomically advances the approved documentation copy.
"""
import argparse
import json
from pathlib import Path
import sys
from . import core, journeys, library
from .contextqa import ContextQAClient, exclusive_json, replace_private_json
from .loop import Store, fingerprint


def collect(client, planned, registry, runs, out, hosts, max_media=50, library_path=None, recording_frames=False):
    if library_path and (Path(library_path)/'latest.json').exists():
        pointer=core.load_json(Path(library_path)/'latest.json')
        version=pointer['version']
        if not isinstance(version,str) or len(version)!=64 or any(c not in '0123456789abcdef' for c in version):
            raise core.Rejected('Invalid library version')
        previous=core.load_json(Path(library_path)/'versions'/version/'version.json')
        if fingerprint({k:v for k,v in previous.items() if k!='version'})!=version:
            raise core.Rejected('Library version changed')
        if previous['project']!=planned['manifest']['project_id']:raise core.Rejected('Library project differs')
        planned=journeys.checked(planned,'plan_digest')
        for article in planned['articles']:
            if article['path'] in previous['documents']:
                article['before']=previous['documents'][article['path']]
                article['base_digest']=fingerprint(article['before'])
        planned=journeys.sealed(planned,'plan_digest')
    out=Path(out); report=journeys.impact(planned,registry)
    if report['unmapped_sections']:raise core.Rejected('Map every affected article to a ContextQA journey')
    ids={j['id'] for j in report['journeys']}
    if not ids or set(runs)!=ids:raise core.Rejected('Supply exactly the affected accepted run IDs')
    source=dict(plan=planned,registry=registry,runs=runs,hosts=hosts,max_media=max_media,recording_frames=recording_frames)
    digest=fingerprint(source);state_path=out/'state.json'
    if state_path.exists():
        state=core.load_json(state_path)
        if state['input_digest']!=digest:raise core.Rejected('Resume inputs changed; use a new workflow directory')
    else:
        if out.exists():raise core.Rejected('Unrecognized workflow directory')
        exclusive_json(out/'inputs.json',source)
        state=dict(schema=1,input_digest=digest,phase='collecting',journeys={})
        replace_private_json(state_path,state)
    try:
        for ident in sorted(ids):
            root=out/'captures'/ident;spec=runs[ident]
            if not (root/'journey-capture.json').exists():
                if root.exists():raise core.Rejected('Partial capture exists; inspect it before resuming in a fresh directory')
                run_record=client.call('getTestPlanResult',id=spec['run_id'])
                if run_record.get('status')!='STATUS_COMPLETED':
                    raise core.Rejected('ContextQA run is not complete; resume after its terminal verdict')
                journeys.capture(client,registry,ident,spec['run_id'],planned['head_sha'],root,spec.get('deployment'))
            record=core.load_json(root/'journey-capture.json');journeys.checked(record)
            state['journeys'][ident]=dict(run_id=spec['run_id'],verdict=record['receipt']['verdict'],deployment_verified=record['deployment_verified'])
            replace_private_json(state_path,state)
            if record['receipt']['verdict']!='passed' or not record['deployment_verified']:
                raise core.Rejected('ContextQA execution or deployment gate failed; latest documentation is unchanged')
            if not (root/'review-recipe.json').exists():journeys.fetch_capture_media(root,hosts,max_media,recording_frames)
        # Private briefing contains local evidence only, never signed download URLs.
        brief=dict(schema=1,task='Write complete task-based guides from these ContextQA executions.',
                   instructions=planned['manifest']['instructions'],articles=planned['articles'],journeys=[])
        for ident in sorted(ids):
            root=out/'captures'/ident
            brief['journeys'].append(dict(id=ident,capture=core.manifest(root),recipe=core.load_json(root/'review-recipe.json'),evidence_directory=str(root.resolve())))
        replace_private_json(out/'authoring-brief.json',brief)
        state.update(phase='awaiting_editorial_review',error=None)
    except core.Rejected as error:
        state.update(phase='blocked',error=str(error));replace_private_json(state_path,state);raise
    replace_private_json(state_path,state)
    return dict(workspace=str(out),phase=state['phase'],brief=str(out/'authoring-brief.json'),new_execution_started=False)


def finalize(out, recipes, specs, reviewer, lib, expected_latest, confirmed=False, *, allow_simulated=False):
    out=Path(out);inputs=core.load_json(out/'inputs.json');state=core.load_json(out/'state.json')
    if fingerprint(inputs)!=state['input_digest']:raise core.Rejected('Workflow input integrity changed')
    if not confirmed:raise core.Rejected('Explicit review of instructions, media and rights is required')
    if set(recipes)!=set(inputs['runs']):raise core.Rejected('Review every collected journey')
    request=dict(recipes=recipes,specs=specs,reviewer=reviewer,library=str(Path(lib).resolve()),expected_latest=expected_latest)
    digest=fingerprint(request)
    recipe_digest=fingerprint(dict(recipes=recipes,reviewer=reviewer))
    if state.get('recipe_digest') and state['recipe_digest']!=recipe_digest:
        raise core.Rejected('Reviewed recipes changed; use a new review workspace')
    if state.get('phase')=='complete':
        if state['finalize_digest']!=digest:raise core.Rejected('Completed workflow is immutable; collect a new refresh')
        return state['result']
    state['recipe_digest']=recipe_digest
    state['finalize_digest']=digest;state['phase']='reviewing';replace_private_json(out/'state.json',state)
    exports={}
    try:
        for ident,recipe in recipes.items():
            target=out/'reviewed'/ident
            if not target.exists():journeys.review_capture(out/'captures'/ident,recipe,target,reviewer,True)
            exports[ident]=str(target.resolve())
        enriched=journeys.evidence_plan(inputs['plan'],inputs['registry'],exports)
        if not allow_simulated and any(e['capture']['execution'].get('transport')=='simulated' for e in enriched['journey_evidence']):
            raise core.Rejected('Finalization requires real ContextQA execution')
        proposal=journeys.editorial_proposal(enriched,specs,exports)
        # Do not auto-answer missing evidence or incomplete quality checks.
        if proposal['questions']:raise core.Rejected('Editorial gates remain: '+'; '.join(proposal['questions']))
        if not proposal['edits']:
            latest=core.load_json(Path(lib)/'latest.json')
            version=latest.get('version')
            if version!=expected_latest or not isinstance(version,str) or len(version)!=64 or any(c not in '0123456789abcdef' for c in version):
                raise core.Rejected('Latest version changed; reconcile the unchanged candidate')
            root=Path(lib)/'versions'/version
            previous=core.load_json(root/'version.json')
            if fingerprint({k:v for k,v in previous.items() if k!='version'})!=version:
                raise core.Rejected('Library version changed')
            if previous['project']!=inputs['plan']['manifest']['project_id'] or previous.get('simulated') and not allow_simulated:
                raise core.Rejected('Library identity or execution policy differs')
            for path,hash_value in previous['file_hashes'].items():
                if fingerprint(core.regular_file(core.asset_file(root/'files',path)).hex())!=hash_value:
                    raise core.Rejected('Library files changed')
            if any(previous['documents'].get(a['path'])!=a['before'] for a in inputs['plan']['articles']):
                raise core.Rejected('Unchanged candidate differs from latest')
            result=dict(updated=False,version=version,latest=str(Path(lib)/'latest.json'),published=False)
            state.update(phase='complete',result=result,error=None)
            replace_private_json(out/'state.json',state)
            replace_private_json(out/'exports.json',exports)
            return result
        prepared=out/'reviews'/fingerprint(specs)
        if not prepared.exists():journeys.prepare(inputs['plan'],inputs['registry'],exports,prepared,editorial_specs=specs)
        store=Store(prepared/'review.db');project=inputs['plan']['manifest']['project_id']
        items=list(store.snapshot(project,'owner')['items'].values())
        if len(items)!=1:raise core.Rejected('Ambiguous review workspace')
        item=items[0];ident=item['id']
        if item['status'] not in ('ready','delivered'):
            for change in item['changes']:
                if change['decision']=='pending':item=store.review(project,'owner',ident,item['version'],'accept',change_id=change['id'])
            if item.get('questions'):
                mechanical='Attach a reviewed ContextQA export for the changed workflow before delivery.'
                if any(q!=mechanical for q in item['questions']):
                    raise core.Rejected('Review questions remain; latest unchanged')
                item=store.review(project,'owner',ident,item['version'],'answer',text='Reviewed ContextQA exports attached and validated against every required journey.')
            item=store.review(project,'owner',ident,item['version'],'ready')
        if not item.get('approval'):store.approve(project,'owner',ident,item['version'],True)
        result=library.advance(prepared,inputs['registry'],exports,lib,expected_latest,allow_simulated=allow_simulated)
        replace_private_json(out/'exports.json',exports)
        state.update(phase='complete',result=result,error=None)
    except core.Rejected as error:
        state.update(phase='blocked',error=str(error));replace_private_json(out/'state.json',state);raise
    replace_private_json(out/'state.json',state)
    return result


def cli():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('collect');c.add_argument('--plan',required=True);c.add_argument('--registry',required=True);c.add_argument('--runs',required=True);c.add_argument('--out',required=True);c.add_argument('--allow-host',action='append',required=True);c.add_argument('--max-media',type=int,default=50);c.add_argument('--library');c.add_argument('--recording-frames',action='store_true')
    f=sub.add_parser('finalize');f.add_argument('--workspace',required=True);f.add_argument('--recipes',required=True);f.add_argument('--editorial-specs',required=True);f.add_argument('--reviewer',required=True);f.add_argument('--library',required=True);f.add_argument('--expected-latest',required=True);f.add_argument('--confirm-content-and-rights',action='store_true')
    a=p.parse_args();read=lambda path:core.load_json(Path(path))
    try:
        if a.command=='collect':
            import os
            result=collect(ContextQAClient(os.environ.get('CONTEXTQA_API_TOKEN')),read(a.plan),read(a.registry),read(a.runs),a.out,a.allow_host,a.max_media,a.library,a.recording_frames)
        else:result=finalize(a.workspace,read(a.recipes),read(a.editorial_specs),a.reviewer,a.library,None if a.expected_latest=='none' else a.expected_latest,a.confirm_content_and_rights)
        print(json.dumps(result,indent=2))
    except (core.Rejected,ValueError,KeyError,OSError) as error:
        print('Documentation workflow stopped: '+str(error),file=sys.stderr);sys.exit(1)

if __name__=='__main__':cli()
