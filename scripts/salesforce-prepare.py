#!/usr/bin/env python3
"""Prepare review-only Salesforce scenarios from local approved context."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cqa_artifacts.core import load_json, Rejected
from cqa_artifacts.salesforce import prepare, draft_guide


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True, type=Path)
    parser.add_argument('--catalog', type=Path, default=Path(__file__).resolve().parents[1]/'examples/salesforce/catalog.json')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.context.is_symlink() or not args.context.is_file() or args.context.stat().st_size > 64 * 1024 * 1024:
        raise Rejected('Context must be a regular JSON file within 64 MiB')
    result = prepare(load_json(args.catalog), json.loads(args.context.read_text()))
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(args.out, 0o700)
    output = args.out/'prepared-scenarios.json'
    output.write_text(json.dumps(result, indent=2)+'\n'); output.chmod(0o600)
    draft_guide(result, args.out/'guide-draft')
    print(json.dumps({'mode':result['mode'], 'executed':False, **result['summary']}))

if __name__ == '__main__':
    try:
        main()
    except (Rejected, OSError, ValueError, KeyError, TypeError):
        print('Preparation rejected: check input schema, credentials, and fresh output path.', file=sys.stderr)
        raise SystemExit(1)
