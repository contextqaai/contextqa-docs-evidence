"""Prepare a real, source-derived review request; never execute tests or publish."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cqa_artifacts.loop import Store

ROOT = Path(__file__).parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, required=True)
    args = parser.parse_args()
    store = Store(args.db)
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    store.create(manifest)
    result = store.ingest('kan', 'owner', json.loads((ROOT / 'event.json').read_text()))
    print(json.dumps(result))

if __name__ == '__main__':
    main()
