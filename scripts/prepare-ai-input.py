"""Extract text only from a digest-verified reviewed export; no AI request."""
import json
import os
import sys
from pathlib import Path
from cqa_artifacts.changes import reviewed

def prepare(source, destination):
    data = reviewed(Path(source))
    payload = {'title': data['title'], 'steps': [
        {'title': step['title'], 'instruction': step['instruction']}
        for step in data['steps']
    ]}
    with open(destination, 'x', encoding='utf8', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        json.dump(payload, stream, indent=2)
        stream.write('\n')
    return payload

if __name__ == '__main__':
    prepare(*sys.argv[1:])
    print('Verified text-only input saved. Review private information before approving AI sharing.')
