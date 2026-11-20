"""Keep immutable ContextQA-backed documentation versions and an atomic latest copy.

Consumes an approved journey review, never arbitrary browser screenshots or drafts.
"""
import argparse
import base64
import difflib
import html
import json
import os
import posixpath
import re
from pathlib import Path, PurePosixPath
import sys
from . import core, journeys
from .loop import Store, fingerprint, path_name
from .contextqa import replace_private_json


def file_path(value):
    if (not isinstance(value,str) or not value or '\\' in value or ':' in value
        or any(ord(c)<32 for c in value) or PurePosixPath(value).is_absolute()
        or any(p in ('','.','..') for p in value.split('/'))):
        raise core.Rejected('Expected a relative bundle file path')
    return value


def render_document(body):
    """Render the generated Markdown subset; never execute raw article HTML."""
    from .guides import CSS
    def inline(value):
        value=html.escape(value)
        pattern=r'(!?)\[([^\]]*)\]\(([^)]+)\)'
        def link(m):
            image,label,target=m.groups()
            # Only local evidence or credential-free HTTPS references.
            from urllib.parse import urlsplit
            u=urlsplit(html.unescape(target))
            if u.scheme not in ('','https') or u.netloc and u.scheme!='https' or u.username or u.password:
                return label
            if image:return '<img src="'+target+'" alt="'+label+'" style="max-width:100%;height:auto" loading="lazy">'
            return '<a href="'+target+'">'+label+'</a>'
        value=re.sub(pattern,link,value)
        return re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',value)
    rows=[];listing=None
    for line in body.splitlines():
        if line.startswith('<!--'):continue
        match=re.match(r'^(\d+\.|-) (.*)',line)
        kind=('ol' if match.group(1)!='-' else 'ul') if match else None
        if listing!=kind:
            if listing:rows.append('</'+listing+'>')
            if kind:rows.append('<'+kind+'>')
            listing=kind
        if match:rows.append('<li>'+inline(match.group(2))+'</li>');continue
        h=re.match(r'^(#{1,6}) (.*)',line)
        if h:
            n=str(len(h.group(1)));rows.append('<h'+n+'>'+inline(h.group(2))+'</h'+n+'>')
        elif line.startswith('> '):rows.append('<aside class="notice">'+inline(line[2:])+'</aside>')
        elif line.strip():rows.append('<p>'+inline(line)+'</p>')
    if listing:rows.append('</'+listing+'>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ContextQA guide</title><style>'+CSS+'</style><main style="max-width:900px;margin:40px auto;padding:0 24px">'+''.join(rows)+'</main></html>'


def advance(review_dir, registry, exports, library, expected_latest, *, allow_simulated=False):
    review_dir=Path(review_dir);library=Path(library)
    planned=core.load_json(review_dir/'plan.json')
    # Revalidate current exports, deployment, source revision and media origins.
    checked=journeys.evidence_plan(planned,registry,exports)
    if not allow_simulated and any(e['capture']['execution'].get('transport')=='simulated' for e in checked['journey_evidence']):
        raise core.Rejected('Latest documentation requires real ContextQA execution')
    project=planned['manifest']['project_id'];store=Store(review_dir/'review.db')
    state=store.snapshot(project,'owner')
    items=list(state['items'].values())
    if len(items)!=1:raise core.Rejected('Expected a single prepared review item')
    item=items[0]
    required={e['export_digest'] for e in checked['journey_evidence']}
    if {e['digest'] for e in item['evidence']}!=required:
        raise core.Rejected('Approved review and validated ContextQA exports differ')
    if library.is_symlink():raise core.Rejected('Library must not be a symlink')
    library.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=library/'.update.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise core.Rejected('Library is locked; inspect the prior update before retrying') from None
    os.close(fd)
    try:
        latest_path=library/'latest.json'
        current=core.load_json(latest_path) if latest_path.exists() else None
        actual=current['version'] if current else None
        if actual!=expected_latest:raise core.Rejected('Latest version changed; regenerate the comparison against the current baseline')
        previous=None;previous_root=None
        if current:
            if not isinstance(actual,str) or len(actual)!=64 or any(c not in '0123456789abcdef' for c in actual):raise core.Rejected('Invalid latest pointer')
            previous_root=library/'versions'/actual
            previous=core.load_json(previous_root/'version.json')
            if previous.get('project')!=project:raise core.Rejected('Library belongs to another project')
            if previous.get('simulated') and not allow_simulated:raise core.Rejected('Cannot promote a simulated library as live documentation')
            if fingerprint({k:v for k,v in previous.items() if k!='version'})!=actual:
                raise core.Rejected('Previous version manifest changed')
            for path,digest in previous['file_hashes'].items():
                file_path(path)
                if fingerprint(core.regular_file(core.asset_file(previous_root/'files',path)).hex())!=digest:
                    raise core.Rejected('Previous version files changed')
        old_docs=previous['documents'] if previous else {}
        bundle=store.bundle(project,'owner',item['id'])
        if previous and previous['source_revision']==planned['head_sha'] and all(old_docs.get(p)==body for p,body in bundle['files'].items()) and all(previous['file_hashes'].get(p)==fingerprint(base64.b64decode(raw,validate=True).hex()) for p,raw in bundle['evidence_files'].items()):
            return dict(updated=False,version=actual,latest=str(latest_path))
        for change in item['changes']:
            if change['decision']=='accepted' and fingerprint(old_docs.get(change['path'],''))!=change['base_digest']:
                # First adoption may start with an existing repository article.
                if previous:raise core.Rejected('Library article differs from the reviewed baseline')
        documents=dict(old_docs)
        if previous is None:
            documents.update({a['path']:a['before'] for a in planned['articles'] if a['before']})
        before=dict(documents);documents.update(bundle['files'])
        files={}
        if previous:
            for path in previous['file_hashes']:files[path]=core.regular_file(core.asset_file(previous_root/'files',path))
        for path,body in documents.items():
            files[path_name(path)]=body.encode()
            files[path+'.html']=render_document(body).encode()
        for path,payload in bundle['evidence_files'].items():files[file_path(path)]=base64.b64decode(payload,validate=True)
        active_media={}
        for path,body in documents.items():
            for target in re.findall(r'\]\(([^)]+)\)',body):
                target=posixpath.normpath(posixpath.join(posixpath.dirname(path),target))
                if target in files and target.endswith(('.png','.jpg','.jpeg','.webp','.mp4','.webm')):
                    active_media[target]=fingerprint(files[target].hex())
        payload=dict(schema=1,active_media=active_media,project=project,parent=actual,source_revision=planned['head_sha'],documents=documents,
                     file_hashes={path:fingerprint(raw.hex()) for path,raw in sorted(files.items())},
                     journeys=[dict(id=e['journey_id'],run_id=e['capture']['execution']['run_id'],export_digest=e['export_digest']) for e in checked['journey_evidence']],
                     evidence_policy='contextqa-only-v1',simulated=allow_simulated)
        # No churn for an identical approved content/evidence replay.
        if previous and payload['file_hashes']==previous['file_hashes'] and payload['source_revision']==previous['source_revision']:
            return dict(updated=False,version=actual,latest=str(latest_path))
        version=fingerprint(payload);payload['version']=version
        destination=library/'versions'/version
        destination.mkdir(parents=True,exist_ok=False,mode=0o700)
        for path,raw in files.items():
            file=core.asset_file(destination/'files',path);file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            file.write_bytes(raw);file.chmod(0o600)
        diff=''.join(''.join(difflib.unified_diff(before.get(p,'').splitlines(True),documents.get(p,'').splitlines(True),fromfile='before/'+p,tofile='after/'+p)) for p in sorted(set(before)|set(documents)))
        (destination/'changes.diff').write_text(diff)
        old_media={p:d for p,d in (previous['file_hashes'] if previous else {}).items() if p.endswith(('.png','.jpg','.jpeg','.webp','.mp4','.webm'))}
        if previous and 'active_media' in previous:old_media=previous['active_media']
        new_media=active_media
        changes=dict(before=actual,after=version,added_media=sorted(set(new_media)-set(old_media)),removed_media=sorted(set(old_media)-set(new_media)),changed_media=sorted(p for p in set(new_media)&set(old_media) if new_media[p]!=old_media[p]),comparison='Text diff and media identity; not automated visual interpretation')
        (destination/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
        rows=[]
        for path in sorted(set(before)|set(documents)):
            if before.get(path)==documents.get(path):continue
            before_view=('<iframe title="Previous guide" src="'+html.escape('../'+actual+'/files/'+path+'.html',quote=True)+'"></iframe>') if previous and path in before else '<p>New document</p>'
            after_view='<iframe title="Current guide" src="'+html.escape('files/'+path+'.html',quote=True)+'"></iframe>'
            rows.append('<h2>'+html.escape(path)+'</h2><div class="pair"><section><h3>Before</h3>'+before_view+'</section><section><h3>After</h3>'+after_view+'</section></div><details><summary>Text changes</summary><pre>'+html.escape(diff)+'</pre></details>')
        for label,media,prefix in [('Before',old_media,'../'+actual+'/files/' if actual else ''),('After',new_media,'files/')]:
            rows.append('<h2>'+label+' evidence</h2>')
            for path in media:
                target=html.escape(prefix+path,quote=True)
                rows.append('<figure>'+('<a href="'+target+'"><img src="'+target+'" alt="'+html.escape(label+' '+path,quote=True)+'"></a>' if path.endswith(('.png','.jpg','.jpeg','.webp')) else '<a href="'+target+'">Recording</a>')+'</figure>')
        (destination/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Documentation before and after</title><style>body{font:16px system-ui;margin:32px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%;max-height:650px}section{min-width:0}iframe{width:100%;height:800px;border:1px solid #ddd;background:white}@media(max-width:850px){.pair{grid-template-columns:1fr}}</style><h1>Documentation before and after</h1><p>ContextQA execution evidence. Text/media comparison does not establish semantic equivalence.</p>'+''.join(rows))
        replace_private_json(destination/'version.json',payload)
        # The visible latest changes only after the complete version is written.
        replace_private_json(latest_path,dict(schema=1,version=version,path='versions/'+version+'/files',comparison='versions/'+version+'/comparison.html'))
        return dict(updated=True,version=version,latest=str(latest_path),comparison=str(destination/'comparison.html'),published=False)
    finally:
        lock.unlink()


def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review',required=True);p.add_argument('--registry',required=True);p.add_argument('--exports',required=True)
    p.add_argument('--library',required=True);p.add_argument('--expected-latest',required=True,help='Current version hash, or none for first adoption')
    a=p.parse_args()
    try:
        print(json.dumps(advance(a.review,core.load_json(Path(a.registry)),core.load_json(Path(a.exports)),a.library,None if a.expected_latest=='none' else a.expected_latest),indent=2))
    except (core.Rejected,ValueError,KeyError,OSError) as error:
        print('Latest documentation unchanged: '+str(error),file=sys.stderr);sys.exit(1)

if __name__=='__main__':cli()
