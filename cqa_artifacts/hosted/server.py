"""Same-origin authenticated API, serving the compiled React application."""
import asyncio
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from psycopg_pool import ConnectionPool
from .auth import Settings, Authenticator
from .store import PostgresStore
from . import onboarding, github_intake, discovery, inventory, workflows, captures
from ..core import Rejected
from ..docs_loop import package_bundle

class BodyLimit:
    def __init__(self, app): self.app=app
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST','PUT','PATCH'):
            return await self.app(scope,receive,send)
        messages=[]; total=0
        while True:
            try: message=await asyncio.wait_for(receive(),timeout=15)
            except asyncio.TimeoutError:
                return await JSONResponse({'detail':'Request timed out'},status_code=408)(scope,receive,send)
            if message['type']=='http.disconnect':return
            total+=len(message.get('body',b''))
            if total>2*1024*1024:
                return await JSONResponse({'detail':'Request exceeds 2 MiB'},status_code=413)(scope,receive,send)
            messages.append(message)
            if not message.get('more_body'): break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope,replay,send)

def create_app(settings=None, pool=None, web_root=None):
    settings=(settings or Settings.from_env()).validate()
    owned=pool is None
    pool=pool or ConnectionPool(settings.database_url,min_size=1,max_size=10,open=False,
                                kwargs={'connect_timeout':5},timeout=10)
    auth=Authenticator(settings)
    @asynccontextmanager
    async def lifespan(app):
        if owned: pool.open(); await asyncio.to_thread(pool.wait,timeout=10)
        yield
        if owned:pool.close()
    app=FastAPI(title='ContextQA Docs API',lifespan=lifespan,docs_url=None,redoc_url=None)
    app.state.pool=pool
    app.add_middleware(BodyLimit)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=[urlsplit(settings.origin).hostname])
    @app.middleware('http')
    async def headers(request, call_next):
        origin=request.headers.get('origin')
        if origin and origin!=settings.origin:
            return JSONResponse({'detail':'Cross-origin request denied'},status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' "+((urlsplit(settings.issuer).scheme+'://'+urlsplit(settings.issuer).netloc) if settings.auth_mode=='oidc' else '')+"; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
        if settings.mode=='production': response.headers['Strict-Transport-Security']='max-age=31536000'
        return response
    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # A validation error may contain a submitted test password.
        return JSONResponse({"detail":"Invalid request. Check the required fields."},status_code=422)
    @app.exception_handler(Rejected)
    async def rejection(request, exc):
        return JSONResponse({'detail':str(exc)},status_code=409)
    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logging.getLogger(__name__).error('Request failed (%s)',type(exc).__name__)
        return JSONResponse({'detail':'Operation failed. Refresh before retrying.'},status_code=500)
    @app.get('/healthz')
    def health():
        with pool.connection() as db:
            ready=db.execute('SELECT version FROM docs_schema_versions WHERE version=5').fetchone()
        if not ready: raise HTTPException(503,'Database migration required')
        return {'status':'ok'}
    @app.get('/api/config')
    def config():
        return dict(auth_mode=settings.auth_mode,authority=settings.issuer,client_id=settings.client_id,
                    scope=settings.scope,redirect_uri=settings.origin+'/auth/callback',audience=settings.audience)
    def membership(org,subject):
        with pool.connection() as db:
            member=db.execute('SELECT role FROM docs_memberships WHERE organization_id=%s AND subject=%s',(org,subject)).fetchone()
        if not member:raise HTTPException(404,'Workspace unavailable')
        return member[0]
    @app.get('/api/projects')
    def projects(subject=Depends(auth)):
        with pool.connection() as db:
            rows=db.execute("SELECT p.organization_id,p.id,p.state->'manifest'->>'name',o.name,m.role FROM docs_projects p JOIN docs_memberships m ON m.organization_id=p.organization_id JOIN docs_organizations o ON o.id=p.organization_id WHERE m.subject=%s ORDER BY o.name,p.id",(subject,)).fetchall()
        return {'subject':subject,'projects':[dict(organization_id=o,id=i,name=n,organization=org,role=role) for o,i,n,org,role in rows]}
    for module in (onboarding, github_intake, discovery, inventory, workflows, captures):
        app.include_router(module.router(pool,auth))
    prefix='/api/orgs/{org}/projects/{project}'
    @app.get(prefix+'/state')
    def state(org:str,project:str,subject=Depends(auth)):
        membership(org,subject)
        return PostgresStore(pool,org).snapshot(project,subject)
    @app.get(prefix+'/audit')
    def audit(org:str,project:str,subject=Depends(auth)):
        membership(org,subject)
        return PostgresStore(pool,org).audit(project,subject)
    @app.post(prefix+'/{action}')
    def mutate(org:str,project:str,action:str,data:dict,subject=Depends(auth)):
        membership(org,subject)
        store=PostgresStore(pool,org); common=(project,subject)
        try:
            if action=='events':
                ident=data.get('id','')
                reserved=isinstance(ident,str) and (ident.startswith('guide:') or re.fullmatch(r'github:.+@[0-9a-f]{40,64}',ident))
                if reserved or {'documentation_destination','discovery_id','source_item_id'} & data.keys():
                    raise HTTPException(400,'Use the verified source or reviewed guide intake for this event.')
                return store.ingest(*common,data)
            if action=='articles':return store.article(*common,data['path'],data['title'],data['body'],data.get('expected'))
            if action=='review':
                if data.get('action') not in ('accept','ignore','undo','edit','comment','answer','assign','ready'):
                    raise HTTPException(400,'Unsupported review action')
                return store.review(*common,data['item_id'],data['version'],data['action'],**data.get('data',{}))
            if action=='approve':return store.approve(*common,data['item_id'],data['version'],data.get('confirmed'))
            if action=='bundle':return Response(package_bundle(store.bundle(*common,data['item_id'])),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="contextqa-reviewed-draft.zip"'})
            if action=='apply-local':return store.apply_local(*common,data['item_id'],data.get('confirmed'))
        except Rejected: raise
        except (KeyError,TypeError,ValueError):raise HTTPException(400,'Invalid request') from None
        raise HTTPException(404,'Unknown action')
    root=Path(web_root or Path(__file__).resolve().parents[2]/'apps/web/dist').resolve()
    @app.get('/{path:path}')
    def frontend(path:str):
        if path.startswith('api/'):raise HTTPException(404,'Unknown route')
        asset=(root/path).resolve()
        if not asset.is_relative_to(root):raise HTTPException(404)
        if asset.is_file():return FileResponse(asset)
        if Path(path).suffix:raise HTTPException(404)
        if (root/'index.html').is_file():return FileResponse(root/'index.html')
        raise HTTPException(503,'Build the React application first')
    return app
