"""Local synthetic end-to-end example; no browser, credential or customer data."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cqa_artifacts import core
from cqa_artifacts.changes import compare


def main():
    root = Path(sys.argv[1])
    if root.exists():
        raise SystemExit('Choose a new demo directory')
    for version, navigation, action in [('a', 'Projects', 'Create project'), ('b', 'Workspace', 'New project')]:
        workspace = root / ('workspace-' + version)
        core.init(workspace, 'Synthetic example — create a project — ' + version)
        core.add_step(workspace, 'Open ' + navigation, 'Select ' + navigation + ' in the left navigation. Synthetic example only.')
        core.add_step(workspace, action, 'Choose ' + action + ', enter an invented project name, and verify the empty project opens.')
        core.approve(workspace, 'Synthetic fixture reviewer', True)
        core.export(workspace, root / ('release-' + version), 'https://docs.example.com/synthetic/' + version)
    context = Path(__file__).with_name('change-context.json')
    print(json.dumps(compare(root / 'release-a', root / 'release-b', context, root / 'change-review')))
    print('Synthetic text-only example created. Add separately reviewed screenshots with add-media and attach for image evidence.')


if __name__ == '__main__':
    main()
