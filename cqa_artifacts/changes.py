"""Compare explicitly paired, reviewed evidence; never infer product correctness."""
import os
import shutil
from pathlib import Path
from . import core


def reviewed(root):
    data = core.clean_export(root)
    receipt = core.load_json(root / 'review-receipt.json')
    if receipt.get('digest') != core.export_digest(data) or not receipt.get('rights_and_media_review_confirmed'):
        raise core.Rejected('Compare requires unchanged reviewed exports with review receipts')
    return data


def compare(before: Path, after: Path, context: Path, out: Path):
    old, new = reviewed(before), reviewed(after)
    info = core.load_json(context)
    required = ('before_version', 'after_version', 'what_changed', 'affected_documents')
    if any(not isinstance(info.get(k), str) or not info[k].strip() for k in required):
        raise core.Rejected('Change context requires versions, what_changed and affected_documents')
    pairs = info.get('step_pairs')
    if not isinstance(pairs, list) or not pairs or len(pairs) > core.MAX_STEPS:
        raise core.Rejected('Explicit step_pairs are required; steps are never paired by position automatically')
    seen_old, seen_new, rows = set(), set(), []
    for pair in pairs:
        a, b = pair.get('before'), pair.get('after')
        for index, data, seen in ((a, old, seen_old), (b, new, seen_new)):
            if index is not None:
                if type(index) is not int or not 1 <= index <= len(data['steps']) or index in seen:
                    raise core.Rejected('Step pairs must be unique valid step numbers or null')
                seen.add(index)
        if a is None and b is None:
            raise core.Rejected('A pair must contain at least one step')
        previous = old['steps'][a-1] if a else None
        current = new['steps'][b-1] if b else None
        status = 'added' if not previous else 'removed' if not current else 'changed' if previous != current else 'unchanged'
        rows.append({'before_step': a, 'after_step': b, 'status': status,
                     'before': previous, 'after': current})
    if len(seen_old) != len(old['steps']) or len(seen_new) != len(new['steps']):
        raise core.Rejected('Map every step explicitly, including additions and removals')
    if out.exists() or out.is_symlink():
        raise core.Rejected('Change output must be a new directory')
    report = {k: core.redact(info[k]) for k in required}
    report.update(schema=1, comparison='Reviewed text and media hashes; not a visual or semantic regression verdict', steps=rows)
    core.private_dir(out)
    core.private_dir(out / 'assets')
    media = {}
    for source, data in ((before, old), (after, new)):
        for item in data['media']:
            media[item['id']] = item
            destination = out / item['path']
            shutil.copyfile(core.asset_file(source, item['path']), destination)
            os.chmod(destination, 0o600)
    comparison_steps = []
    for row in rows:
        for label, step in [('Before', row['before']), ('After', row['after'])]:
            if step:
                comparison_steps.append(dict(step, title=label + ' — ' + step['title']))
    (out / 'index.html').write_text(core.render({'title': 'Before and after — reviewed evidence', 'steps': comparison_steps, 'media': list(media.values())}))
    os.chmod(out / 'index.html', 0o600)
    core.write_json(out / 'changes.json', report)
    lines = ['# Documentation refresh draft', '', 'Human review required before updating documentation.', '']
    for k in required:
        lines += [f'**{k.replace("_", " ").title()}:** {core.markdown_plain(report[k])}', '']
    for row in rows:
        lines += [f'## {row["status"].title()}: step {row["before_step"]} → {row["after_step"]}', '']
        for label, step in [('Before', row['before']), ('After', row['after'])]:
            if step:
                lines += [f'**{label}:** {core.markdown_plain(step["title"])}', '', core.markdown_plain(step['instruction']), '']
        lines += ['Review: replace affected screenshots, verify instructions, links, alt text and localization; retain historical version where needed.', '']
    (out / 'refresh-draft.md').write_text('\n'.join(lines))
    os.chmod(out / 'refresh-draft.md', 0o600)
    return {'compared': True, 'steps': len(rows), 'changed': sum(r['status'] != 'unchanged' for r in rows), 'media_copied': True, 'requires_documentation_review': True}
