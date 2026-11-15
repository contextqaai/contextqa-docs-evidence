#!/usr/bin/env python3
"""Convert a private hydrated SX360 snapshot to review-only schema context."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cqa_artifacts.salesforce import context_from_sx360
from cqa_artifacts.core import Rejected

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.snapshot.is_symlink() or args.snapshot.stat().st_size>256*1024*1024:
        raise Rejected('Snapshot must be a regular bounded file')
    result=context_from_sx360(json.loads(args.snapshot.read_text()))
    fd=os.open(args.out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'mode':'schema_only','objects':len(result['objects']),'confirmedRules':0,'executed':False}))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError):
        print('Conversion rejected: check hydrated snapshot and fresh private output path.',file=sys.stderr)
        raise SystemExit(1)
