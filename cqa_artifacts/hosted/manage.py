"""Operator-only migrations, provisioning, and reviewed capture attachment."""
import argparse
import json
import os
from pathlib import Path
from psycopg_pool import ConnectionPool
from .store import PostgresStore

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='command',required=True)
    migrate=sub.add_parser('migrate');migrate.add_argument('--file',type=Path,default=Path('migrations/001_hosted.sql'))
    seed=sub.add_parser('provision');seed.add_argument('--organization',required=True);seed.add_argument('--name',required=True);seed.add_argument('--subject',required=True);seed.add_argument('--manifest',type=Path,required=True);seed.add_argument('--event',type=Path)
    member=sub.add_parser('member');member.add_argument('--organization',required=True);member.add_argument('--subject',required=True);member.add_argument('--role',choices=['admin','editor','contributor'],required=True)
    capture=sub.add_parser('evidence');capture.add_argument('--organization',required=True);capture.add_argument('--project',required=True);capture.add_argument('--subject',required=True);capture.add_argument('--item',required=True);capture.add_argument('--version',type=int,required=True);capture.add_argument('--export',type=Path,required=True)
    args=parser.parse_args()
    with ConnectionPool(os.environ['DATABASE_URL']) as pool:
        if args.command=='migrate':
            with pool.connection() as db,db.transaction():
                db.execute('SELECT pg_advisory_xact_lock(721904882)')
                db.execute(args.file.read_text())
            print('Schema version 1 applied');return
        if args.command=='evidence':
            result=PostgresStore(pool,args.organization).attach_evidence(args.project,args.subject,args.item,args.version,args.export)
            print(json.dumps({'id':result['id'],'version':result['version'],'status':result['status']}));return
        import re
        if not re.fullmatch('[a-zA-Z0-9_-]{1,80}',args.organization):raise ValueError('Use an organization slug')
        if args.command=='member':
            with pool.connection() as db:
                db.execute('INSERT INTO docs_memberships VALUES(%s,%s,%s) ON CONFLICT(organization_id,subject) DO UPDATE SET role=EXCLUDED.role',(args.organization,args.subject,args.role))
            print('Organization membership updated');return
        manifest=json.loads(args.manifest.read_text())
        with pool.connection() as db,db.transaction():
            db.execute('INSERT INTO docs_organizations(id,name) VALUES(%s,%s) ON CONFLICT DO NOTHING',(args.organization,args.name))
            # Never promote an existing account implicitly.
            db.execute("INSERT INTO docs_memberships VALUES(%s,%s,'admin') ON CONFLICT DO NOTHING",(args.organization,args.subject))
            exists=db.execute('SELECT 1 FROM docs_projects WHERE organization_id=%s AND id=%s',(args.organization,manifest['project_id'])).fetchone()
        store=PostgresStore(pool,args.organization)
        if not exists:store.create(manifest,args.subject)
        if args.event:
            result=store.ingest(manifest['project_id'],args.subject,json.loads(args.event.read_text()))
            print(json.dumps(result))
        print('Workspace provisioned')

if __name__=='__main__':main()
