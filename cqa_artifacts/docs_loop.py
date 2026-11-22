"""Local operator CLI and loopback review application."""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import sys
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit
from .core import Rejected
from .loop import Store, encoded

UI=Path(__file__).with_name('loop_ui')


def package_bundle(bundle):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('delivery.json',json.dumps({k:v for k,v in bundle.items() if k!='evidence_files'},indent=2))
        for path,payload in bundle.get('evidence_files',{}).items():
            z.writestr(path,base64.b64decode(payload,validate=True))
        z.writestr('changes.patch',bundle['patch'])
        for path,body in bundle['files'].items():
            z.writestr('docs/'+path,body)
    return stream.getvalue()


def make_server(store, project, actor, port, token=None):
    store.snapshot(project,actor)
    token=token or secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        server_version='ContextQA Docs Loop'
        def log_message(self,*args):
            pass  # URLs and credentials do not enter access logs.
        def reply(self,status,body,ctype='application/json'):
            if isinstance(body,(dict,list)):
                body=json.dumps(body).encode()
            if isinstance(body,str):
                body=body.encode()
            self.send_response(status)
            self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers(); self.wfile.write(body)
        def guard(self,auth=True):
            host='127.0.0.1:'+str(self.server.server_port)
            if self.headers.get('Host')!=host:
                raise Rejected('Invalid Host')
            origin=self.headers.get('Origin')
            if origin and origin!='http://'+host:
                raise Rejected('Cross-origin request denied')
            if auth and not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                raise Rejected('Session token required')
        def do_GET(self):
            try:
                path=urlsplit(self.path).path
                self.guard(auth=path.startswith('/api/'))
                if path=='/api/state':
                    self.reply(200,store.snapshot(project,actor))
                elif path=='/api/audit':
                    self.reply(200,store.audit(project,actor))
                elif path in ('/','/app.js','/ui-core.js','/style.css','/logo.svg'):
                    if path=='/logo.svg':
                        asset=Path(__file__).with_name('brand')/'contextqa-logo.svg'; mime='image/svg+xml'
                    else:
                        asset=UI/({'/':'index.html'}.get(path,path[1:])); mime={'.html':'text/html; charset=utf-8','.js':'application/javascript','.css':'text/css'}[asset.suffix]
                    self.reply(200,asset.read_bytes(),mime)
                else:
                    self.reply(404,{'error':'Not found'})
            except Rejected as exc:
                self.reply(403,{'error':str(exc)})
        def do_POST(self):
            try:
                self.guard()
                if self.headers.get('Content-Type')!='application/json':
                    raise Rejected('JSON required')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2*1024*1024:
                    raise Rejected('Request exceeds bounds')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):
                    raise Rejected('Object required')
                path=urlsplit(self.path).path
                if path=='/api/events':
                    result=store.ingest(project,actor,data)
                elif path=='/api/articles':
                    result=store.article(project,actor,data['path'],data['title'],data['body'],data.get('expected'))
                elif path=='/api/review':
                    result=store.review(project,actor,data['item_id'],data['version'],data['action'],**data.get('data',{}))
                elif path=='/api/approve':
                    result=store.approve(project,actor,data['item_id'],data['version'],data.get('confirmed'))
                elif path=='/api/bundle':
                    result=package_bundle(store.bundle(project,actor,data['item_id']))
                    self.reply(200,result,'application/zip'); return
                elif path=='/api/apply-local':
                    result=store.apply_local(project,actor,data['item_id'],data.get('confirmed'))
                else:
                    self.reply(404,{'error':'Not found'}); return
                self.reply(200,result)
            except (Rejected,ValueError,KeyError,TypeError) as exc:
                self.reply(400,{'error':str(exc) if isinstance(exc,Rejected) else 'Invalid request'})
            except Exception:
                self.reply(500,{'error':'Operation failed; inspect local state before retrying'})
    server=HTTPServer(('127.0.0.1',port),Handler)
    server.session_token=token
    return server


def main():
    p=argparse.ArgumentParser(description='ContextQA documentation loop — local operator workspace')
    p.add_argument('--db',type=Path,default=Path('private/docs-loop.db'))
    p.add_argument('--project',default='demo')
    p.add_argument('--actor',default='owner')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('init','ingest','article','video'):
        c=sub.add_parser(name); c.add_argument('file',type=Path)
    c=sub.add_parser('github'); c.add_argument('file',type=Path); c.add_argument('--signature',required=True); c.add_argument('--delivery',required=True)
    c=sub.add_parser('member'); c.add_argument('name'); c.add_argument('role',choices=['admin','editor','contributor'])
    c=sub.add_parser('review'); c.add_argument('item'); c.add_argument('action',choices=['accept','ignore','undo','edit','comment','answer','assign','ready']); c.add_argument('--version',required=True,type=int); c.add_argument('--data',default='{}')
    c=sub.add_parser('evidence'); c.add_argument('item'); c.add_argument('export',type=Path); c.add_argument('--version',required=True,type=int)
    c=sub.add_parser('approve'); c.add_argument('item'); c.add_argument('--version',required=True,type=int); c.add_argument('--confirm-content-and-rights',action='store_true')
    c=sub.add_parser('bundle'); c.add_argument('item'); c.add_argument('out',type=Path)
    c=sub.add_parser('apply-local'); c.add_argument('item'); c.add_argument('--confirm',action='store_true')
    c=sub.add_parser('draft-pr'); c.add_argument('item'); c.add_argument('--checkout',type=Path,required=True); c.add_argument('--base-sha',required=True); c.add_argument('--base-ref',default='main'); c.add_argument('--branch',required=True); c.add_argument('--journal',type=Path,required=True); c.add_argument('--confirm-create-draft-pr',action='store_true')
    c=sub.add_parser('serve'); c.add_argument('--port',type=int,default=8765)
    sub.add_parser('state'); sub.add_parser('audit')
    a=p.parse_args(); store=Store(a.db); common=(a.project,a.actor)
    data=json.loads(a.file.read_text()) if a.command in ('init','ingest','article','video') else None
    if a.command=='init': result=store.create(data,a.actor)
    elif a.command=='ingest': result=store.ingest(*common,data)
    elif a.command=='article': result=store.article(*common,**data)
    elif a.command=='member': result=store.member(*common,a.name,a.role)
    elif a.command=='state': result=store.snapshot(*common)
    elif a.command=='audit': result=store.audit(*common)
    elif a.command=='review': result=store.review(*common,a.item,a.version,a.action,**json.loads(a.data))
    elif a.command=='approve': result=store.approve(*common,a.item,a.version,a.confirm_content_and_rights)
    elif a.command=='evidence': result=store.attach_evidence(*common,a.item,a.version,a.export)
    elif a.command=='apply-local': result=store.apply_local(*common,a.item,a.confirm)
    elif a.command=='bundle':
        if a.out.exists(): raise Rejected('Choose a new bundle path')
        payload=package_bundle(store.bundle(*common,a.item))
        with a.out.open('xb') as f: f.write(payload)
        os.chmod(a.out,0o600)
        result={'bundle':str(a.out),'published':False,'sha256':hashlib.sha256(payload).hexdigest()}
    elif a.command=='video':
        from .loop_sources import transcript_event
        result=[store.ingest(*common,e) for e in transcript_event(**data)]
    elif a.command=='github':
        from .loop_sources import github_event
        manifest=store.snapshot(*common)['manifest']
        event=github_event(a.file.read_bytes(),a.signature,os.environ.get('DOCS_LOOP_WEBHOOK_SECRET'),manifest['repository'],a.delivery)
        result=store.ingest(*common,event)
    elif a.command=='draft-pr':
        from .loop_git import deliver
        if not a.confirm_create_draft_pr: raise Rejected('Explicit draft-PR delivery approval required')
        snapshot=store.snapshot(*common)
        result=deliver(store.bundle(*common,a.item),a.checkout,snapshot['manifest']['repository'],a.base_sha,a.branch,a.journal,approved=True,base_ref=a.base_ref)
    elif a.command=='serve':
        server=make_server(store,*common,a.port)
        print(f'Open http://127.0.0.1:{server.server_port}/#{server.session_token}',flush=True)
        print('Local operator session. Do not expose this server publicly. Ctrl-C to stop.',flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.server_close()
        return
    print(json.dumps(result,indent=2))


def cli():
    try: main()
    except (Rejected,OSError,ValueError) as e:
        print(str(e),file=sys.stderr); raise SystemExit(1)

if __name__=='__main__': cli()
