"""Evidence-linked editorial guides: deterministic drafts, review gates and impact.

This compiler does not invent prose, inspect pixels or certify factual accuracy.
An author/agent supplies a structured guide and explicit observation records.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from .core import Rejected, asset_file, regular_file, markdown_plain
from .loop import fingerprint


def require(condition, message):
    if not condition:
        raise Rejected(message)


def plain(value):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= 16000,
            'Guide text must be nonempty and bounded')
    return value


def slug(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', value), 'Invalid stable ID')
    return value


def url(value):
    p = urlsplit(plain(value))
    require(p.scheme == 'https' and p.hostname and not p.username and not p.password
            and not p.query, 'Source links must be credential-free HTTPS without query strings')
    return value


def indexed(rows):
    require(isinstance(rows, list) and len(rows) <= 200, 'Expected bounded records')
    result = {}
    for row in rows:
        require(isinstance(row, dict), 'Expected record')
        ident = slug(row.get('id'))
        require(ident not in result, 'Duplicate stable ID')
        result[ident] = row
    return result


def validate(spec, evidence_root):
    require(spec.get('schema') == 'editorial-guide-v1', 'Unknown guide schema')
    slug(spec.get('id'))
    for key in ('title', 'audience', 'goal', 'summary'):
        plain(spec.get(key))
    require(isinstance(spec.get('prerequisites'), list) and spec['prerequisites'], 'Prerequisites required')
    for item in spec['prerequisites']: plain(item)
    sources = indexed(spec.get('sources')); figures = indexed(spec.get('figures'))
    sections = indexed(spec.get('sections'))
    require(sections, 'Guide sections required')
    blockers = []
    for source in sources.values():
        require(source.get('kind') in ('product-reference', 'browser-observation', 'contextqa-run'), 'Unknown evidence kind')
        url(source.get('url')); plain(source.get('observed_at')); plain(source.get('summary'))
        if source['kind'] == 'contextqa-run':
            require(isinstance(source.get('run_id'), int) and source['run_id'] > 0, 'Run ID required')
            if source.get('verdict') != 'passed' or source.get('deployment_verified') is not True:
                blockers.append('Unverified or failed execution: ' + source['id'])
    assets = {}
    for ident, figure in figures.items():
        require(figure.get('source_id') in sources, 'Figure source missing')
        for key in ('caption', 'alt', 'purpose'): plain(figure.get(key))
        require(all(type(figure.get(k)) is int and 1 <= figure[k] <= 20000 for k in ('width','height')), 'Image dimensions required')
        path = figure.get('path')
        require(isinstance(path, str) and re.fullmatch(r'[A-Za-z0-9_./-]+', path), 'Invalid image path')
        raw = regular_file(asset_file(Path(evidence_root), path), 12 * 1024 * 1024)
        require(raw.startswith(b'\xff\xd8\xff') or raw.startswith(b'\x89PNG\r\n\x1a\n'), 'Expected PNG or JPEG evidence')
        digest = hashlib.sha256(raw).hexdigest()
        require(figure.get('sha256') == digest, 'Screenshot changed; inspect and update its evidence record')
        suffix = '.jpg' if raw.startswith(b'\xff\xd8\xff') else '.png'
        assets[ident] = dict(path='assets/' + digest + suffix, raw=raw)
        for flag in ('privacy_reviewed', 'state_reviewed', 'readability_reviewed'):
            if figure.get(flag) is not True: blockers.append(ident + ': ' + flag + ' required')
    for ident, section in sections.items():
        plain(section.get('title'))
        require(section.get('kind') in ('procedure', 'concept', 'verification', 'troubleshooting'), 'Unknown section type')
        refs = section.get('source_ids')
        require(isinstance(refs, list) and refs and set(refs) <= sources.keys(), 'Every section needs known sources')
        require(isinstance(section.get('paragraphs'), list) and section['paragraphs'], 'Section explanation required')
        for p in section['paragraphs']: plain(p)
        refs = section.get('figure_ids', [])
        require(isinstance(refs, list) and set(refs) <= figures.keys(), 'Unknown figure reference')
        require(all(figures[f]['source_id'] in section['source_ids'] for f in refs), 'Figure and section sources disagree')
        if section['kind'] == 'procedure':
            require(isinstance(section.get('steps'), list) and section['steps'], 'Procedure actions required')
            for step in section['steps']: plain(step)
            plain(section.get('expected'))
        if section.get('requires_execution') is True and not any(
                sources[s]['kind'] == 'contextqa-run' and sources[s].get('verdict') == 'passed'
                and sources[s].get('deployment_verified') is True for s in section['source_ids']):
            blockers.append(ident + ': matching passed deployment-bound execution missing')
    for link in spec.get('related', []): plain(link.get('title')); url(link.get('url'))
    review = spec.get('review', {})
    for flag in ('editorial', 'independent_task_completion'):
        if review.get(flag) is not True: blockers.append(flag + ' review pending')
    return sources, figures, sections, assets, blockers


CSS = '''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fff;color:#243044;font:17px/1.7 system-ui,sans-serif}header{border-bottom:1px solid #e4e7ec;padding:18px 32px;font-size:15px}header strong{color:#4535b7}.layout{display:grid;grid-template-columns:220px minmax(0,850px);gap:52px;max-width:1200px;margin:44px auto;padding:0 28px}nav{position:sticky;top:24px;align-self:start;font-size:14px}nav a{display:block;color:#526077;text-decoration:none;padding:7px 0}nav a:hover,a{color:#4535b7}h1{font-size:42px;line-height:1.15;letter-spacing:-1.3px;margin:14px 0 24px}h2{font-size:26px;line-height:1.3;letter-spacing:-.5px;margin:48px 0 16px;scroll-margin-top:24px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#6a5fc4;font-weight:700}.lead{font-size:20px;color:#536078}.notice,.checkpoint{border-left:3px solid #7569d4;background:#f6f5fc;padding:14px 18px;margin:24px 0}.notice{font-size:14px;background:#fff9ec;border-color:#d4a947}li{padding:5px 0}figure{margin:26px 0}figure a{display:block;border:1px solid #e3e5ec;border-radius:8px;overflow:hidden}figure img{display:block;max-width:100%;height:auto;margin:auto}figcaption{font-size:14px;color:#626d7c;margin-top:10px}.sources{font-size:13px;color:#626d7c}footer{border-top:1px solid #e4e7ec;margin-top:44px;padding:20px 0;font-size:14px}details{font-size:14px;margin:28px 0}summary{cursor:pointer} @media(max-width:850px){.layout{display:block;padding:0 20px;margin:24px auto}nav{position:static;border-bottom:1px solid #e4e7ec;padding-bottom:18px}nav a{display:inline-block;margin-right:16px}h1{font-size:34px}}'''


def compile_guide(spec, evidence_root):
    sources, figures, sections, assets, blockers = validate(spec, evidence_root)
    esc = html.escape
    md = ['# ' + markdown_plain(spec['title']), '', markdown_plain(spec['summary']), '',
          '> Editorial draft. See quality-report.json for evidence and review gaps.', '',
          '## Before you begin', ''] + ['- ' + markdown_plain(p) for p in spec['prerequisites']]
    body = ['<p class="eyebrow">ContextQA / How-to guide</p>', '<h1>' + esc(spec['title']) + '</h1>',
            '<p class="lead">' + esc(spec['summary']) + '</p>',
            '<p><strong>For:</strong> ' + esc(spec['audience']) + '</p>',
            '<div class="notice"><strong>Editorial draft.</strong> ' + str(len(blockers)) + ' evidence or review gates remain. '
            'Screenshots show observed UI states; they do not establish a successful test run.</div>',
            '<h2 id="before-you-begin">Before you begin</h2><ul>' + ''.join('<li>' + esc(p) + '</li>' for p in spec['prerequisites']) + '</ul>']
    manifest = {}
    for ident, s in sections.items():
        md += ['', '<!-- docs:section:' + ident + ' -->', '## ' + markdown_plain(s['title']), '']
        body += ['<section id="' + ident + '"><h2>' + esc(s['title']) + '</h2>']
        for p in s['paragraphs']:
            md += [markdown_plain(p), '']; body += ['<p>' + esc(p) + '</p>']
        if s.get('steps'):
            md += [str(i) + '. ' + markdown_plain(p) for i,p in enumerate(s['steps'],1)]
            body += ['<ol>' + ''.join('<li>' + esc(p) + '</li>' for p in s['steps']) + '</ol>']
        if s.get('expected'):
            md += ['', '**Check your progress:** ' + markdown_plain(s['expected']), '']
            body += ['<div class="checkpoint"><strong>Check your progress:</strong> ' + esc(s['expected']) + '</div>']
        for fid in s.get('figure_ids', []):
            f = figures[fid]; path = assets[fid]['path']
            md += ['![' + markdown_plain(f['alt']) + '](' + path + ')', '', markdown_plain(f['caption']), '']
            body += ['<figure><a href="' + path + '" target="_blank" rel="noopener"><img src="' + path + '" alt="' + esc(f['alt'],quote=True) + '" width="' + str(f['width']) + '" height="' + str(f['height']) + '" loading="lazy"></a><figcaption>' + esc(f['caption']) + '</figcaption></figure>']
        body += ['</section>']
        manifest[ident] = dict(content_digest=fingerprint(s), source_digests={r:fingerprint(sources[r]) for r in s['source_ids']},
                              figure_digests={f:fingerprint(figures[f]) for f in s.get('figure_ids', [])})
    body += ['<h2 id="related">Continue learning</h2><ul>']; md += ['', '## Continue learning', '']
    for link in spec.get('related', []):
        body += ['<li><a href="' + esc(link['url'],quote=True) + '">' + esc(link['title']) + '</a></li>']
        md += ['- [' + markdown_plain(link['title']) + '](' + link['url'] + ')']
    body += ['</ul><details><summary>Evidence and review status</summary><ul>']
    for source in sources.values():
        body += ['<li><a href="' + esc(source['url'],quote=True) + '">' + esc(source['id']) + '</a> — ' + esc(source['kind'] + ': ' + source['summary']) + '</li>']
    body += ['</ul><ul>' + ''.join('<li>' + esc(b) + '</li>' for b in blockers) + '</ul></details>']
    toc = '<a href="#before-you-begin">Before you begin</a>' + ''.join('<a href="#' + k + '">' + esc(s['title']) + '</a>' for k,s in sections.items())
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(spec['title']) + '</title><style>' + CSS + '</style><body><header><strong>ContextQA</strong> &nbsp; / &nbsp; Documentation</header><div class="layout"><nav aria-label="On this page">' + toc + '</nav><main>' + ''.join(body) + '<footer>Generated from an evidence-linked editorial specification. Open any screenshot to inspect it at full size.</footer></main></div></body></html>'
    report = dict(schema=1,guide_id=spec['id'],spec_digest=fingerprint(spec),review_required=True,
                  publication_ready=False, structural_checks_passed=True, blockers=blockers,
                  document_digest=fingerprint({k:spec.get(k) for k in ('title','audience','goal','summary','prerequisites','related','review')}),
                  section_order=list(sections),
                  notes=['Review flags are operator attestations, not automated vision or factual verification.',
                         'This compiler does not grant publication approval.'], sections=manifest)
    return dict(markdown='\n'.join(md)+'\n', html=page, report=report, assets=assets)


def impact(before, after):
    require(before['guide_id'] == after['guide_id'], 'Cannot compare unrelated guides')
    rows=[]
    for ident in sorted(set(before['sections']) | set(after['sections'])):
        a=before['sections'].get(ident); b=after['sections'].get(ident)
        if a==b: continue
        reasons = ['added' if a is None else 'removed'] if a is None or b is None else [
            key for key in ('content_digest','source_digests','figure_digests') if a[key] != b[key]]
        rows.append(dict(section=ident,reasons=reasons))
    document_changed=before.get('document_digest')!=after.get('document_digest')
    order_changed=before.get('section_order')!=after.get('section_order')
    changed=bool(rows) or document_changed or order_changed
    return dict(guide_id=after['guide_id'],changed_sections=rows,no_change=not changed,
                document_changed=document_changed,section_order_changed=order_changed,
                review_required=changed,publication_ready=False)


def build(spec_path, evidence_root, output):
    spec=json.loads(regular_file(Path(spec_path), 2*1024*1024))
    from .changes import reviewed
    from .journeys import checked
    root=Path(evidence_root)
    receipt_path=root/'journey-review.json'
    require(receipt_path.exists(), 'ContextQA-only: build requires a reviewed journey export, not browser captures')
    receipt=json.loads(regular_file(receipt_path,2*1024*1024));checked(receipt)
    capture=reviewed(root)
    require(receipt.get('evidence_policy')=='contextqa-only-v1' and receipt.get('export_digest')==fingerprint(capture), 'ContextQA artifact provenance missing or changed')
    require(capture.get('execution',{}).get('verdict')=='passed' and capture['execution'].get('transport')!='simulated', 'Real successful ContextQA execution required')
    require(not any(s.get('kind')=='browser-observation' for s in spec['sources']), 'Manual browser observations are outside this workflow')
    execution=capture['execution'];deployment=receipt.get('deployment',{})
    require(deployment.get('confirmed') is True and deployment.get('run_id')==execution.get('run_id')
            and deployment.get('commit_sha')==receipt.get('head_sha'), 'Deployment/run binding missing')
    for source in spec['sources']:
        if source.get('kind')=='contextqa-run':
            require(source.get('run_id')==execution.get('run_id') and source.get('journey_id')==receipt.get('journey_id'), 'Source does not match the reviewed ContextQA journey')
    for figure in spec['figures']:
        source=next((s for s in spec['sources'] if s['id']==figure['source_id']),None)
        require(source and source.get('kind')=='contextqa-run' and source.get('journey_id')==receipt.get('journey_id'), 'Figure must cite the reviewed ContextQA run')
        media=next((m for m in capture['media'] if m['id']==figure.get('media_id')),None)
        require(media and media['path']==figure['path'] and media['kind']=='screenshot', 'Figure must resolve to a ContextQA export screenshot')
        require(any(o.get('media_id')==media['id'] for o in receipt.get('media_origins',[])), 'Figure download provenance missing')
    result=compile_guide(spec,evidence_root)
    target=Path(output)
    require(not target.exists(), 'Choose a new output directory')
    target.mkdir(parents=True,mode=0o700); (target/'assets').mkdir(mode=0o700)
    for asset in result['assets'].values(): (target/asset['path']).write_bytes(asset['raw'])
    (target/'guide.md').write_text(result['markdown'])
    (target/'index.html').write_text(result['html'])
    (target/'quality-report.json').write_text(json.dumps(result['report'],indent=2)+'\n')
    return result['report']


def cli():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('build');p.add_argument('--spec',required=True);p.add_argument('--evidence-root',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('impact');p.add_argument('--before',required=True);p.add_argument('--after',required=True)
    a=parser.parse_args()
    try:
        if a.command=='build': result=build(a.spec,a.evidence_root,a.out)
        else: result=impact(json.loads(Path(a.before).read_text()),json.loads(Path(a.after).read_text()))
        print(json.dumps(result,indent=2))
    except (Rejected,KeyError,TypeError,ValueError) as e:
        print('Guide rejected: '+str(e),file=sys.stderr);sys.exit(1)

if __name__=='__main__': cli()
