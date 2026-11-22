import concurrent.futures
import copy
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import Mock
import uuid
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from fastapi import HTTPException
from psycopg_pool import ConnectionPool
from starlette.requests import Request
from cqa_artifacts.core import Rejected
from cqa_artifacts.hosted.auth import Settings,Authenticator
from cqa_artifacts.hosted.server import create_app
from cqa_artifacts.hosted.store import PostgresStore

ROOT=Path(__file__).resolve().parents[1]

class AuthTests(unittest.TestCase):
    def test_production_rejects_development_auth(self):
        with self.assertRaises(ValueError):Settings('postgres://db','https://app.example.com',auth_mode='development',dev_token='a'*40).validate()
    def test_production_requires_complete_oidc(self):
        with self.assertRaises(ValueError):Settings('postgres://db','https://app.example.com').validate()
    def test_onboarding_receipt_distinguishes_a_new_session_from_an_old_wizard_result(self):
        from cqa_artifacts.hosted.discovery import onboarding_receipt
        session=str(uuid.uuid4())
        step=dict(status='COMPLETED',sessionId=session,runnerTestCaseId=1,uploadRequirementId=2)
        self.assertEqual(onboarding_receipt({},dict(appDetails=step)),('submitted',None,1,2,session))
        self.assertEqual(onboarding_receipt(step,dict(appDetails=step))[0],'needs_reconciliation')

    def test_validated_signature_audience_expiry_and_scope(self):
        settings=Settings('postgres://db','https://app.example.com',issuer='https://id.example.com',audience='docs-api',client_id='docs-web',jwks_url='https://id.example.com/keys').validate()
        auth=Authenticator(settings);key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        auth.jwks=Mock();auth.jwks.get_signing_key_from_jwt.return_value.key=key.public_key()
        claims=dict(sub='reviewer',iss=settings.issuer,aud='docs-api',iat=int(time.time()),exp=int(time.time())+300,scope='docs:read')
        def request(payload,method='GET'):
            token=jwt.encode(payload,key,algorithm='RS256')
            return Request({'type':'http','method':method,'headers':[(b'authorization',('Bearer '+token).encode())]})
        self.assertEqual(auth(request(claims)),'reviewer')
        for values,method in [({'aud':'other'},'GET'),({'exp':0},'GET'),({},'POST'),({'iss':'https://other.example.com'},'GET')]:
            with self.assertRaises(HTTPException):auth(request({**claims,**values},method))

@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'),'requires isolated PostgreSQL')
class PostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool=ConnectionPool(os.environ['TEST_DATABASE_URL'])
        with cls.pool.connection() as db:
            for migration in sorted((ROOT/'migrations').glob('*.sql')):db.execute(migration.read_text())
    @classmethod
    def tearDownClass(cls):cls.pool.close()
    def setUp(self):
        self.org='test-'+uuid.uuid4().hex;self.other='test-'+uuid.uuid4().hex
        with self.pool.connection() as db:
            for org,subject in [(self.org,'alice'),(self.other,'bob')]:
                db.execute('INSERT INTO docs_organizations(id,name) VALUES(%s,%s)',(org,org))
                db.execute("INSERT INTO docs_memberships VALUES(%s,%s,'admin')",(org,subject))
        self.addCleanup(self.cleanup)
        self.manifest=json.loads((ROOT/'examples/kan-pr15/manifest.json').read_text());self.manifest['project_id']='shared-name'
        self.store=PostgresStore(self.pool,self.org);self.store.create(self.manifest,'alice')
        PostgresStore(self.pool,self.other).create(self.manifest,'bob')
        self.event=dict(id='test-event',source='manual',title='Review a change',text='Review source change',edits=[dict(path='guide.md',before='',after='# Guide\n\nReviewed text.\n',reason='Synthetic integration test')])
        self.settings=Settings(os.environ['TEST_DATABASE_URL'],'http://127.0.0.1:8080',mode='development',auth_mode='development',dev_token='a'*40,dev_subject='alice')
        self.client=TestClient(create_app(self.settings,self.pool),base_url='http://127.0.0.1:8080')
        self.headers={'Authorization':'Bearer '+'a'*40};self.prefix='/api/orgs/'+self.org+'/projects/shared-name/'
    def cleanup(self):
        self.client.close()
        with self.pool.connection() as db:db.execute('DELETE FROM docs_organizations WHERE id IN(%s,%s)',(self.org,self.other))
    def test_tenant_isolation_and_authentication(self):
        self.assertEqual(self.client.get(self.prefix+'state').status_code,401)
        self.assertEqual(self.client.get('/api/orgs/'+self.other+'/projects/shared-name/state',headers=self.headers).status_code,404)
        self.assertEqual(self.client.get(self.prefix+'state',headers=self.headers).status_code,200)
        projects=self.client.get('/api/projects',headers=self.headers).json()['projects']
        self.assertEqual([p['organization_id'] for p in projects],[self.org])
    def test_concurrent_duplicate_events_are_atomic(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as workers:
            results=list(workers.map(lambda _:self.store.ingest('shared-name','alice',self.event),range(6)))
        self.assertEqual(len({r['item_id'] for r in results}),1)
        self.assertEqual(sum(not r['duplicate'] for r in results),1)
    def test_versions_and_baselines_survive_reconnect(self):
        result=self.store.ingest('shared-name','alice',self.event)
        new=PostgresStore(self.pool,self.org)
        item=new.review('shared-name','alice',result['item_id'],1,'accept',change_id='1')
        with self.assertRaises(Rejected):self.store.review('shared-name','alice',item['id'],1,'ignore',change_id='1')
        self.assertEqual(new.snapshot('shared-name','alice')['items'][item['id']]['version'],2)
    def test_membership_revocation_takes_effect(self):
        self.store.ingest('shared-name','alice',self.event)
        with self.pool.connection() as db:db.execute('DELETE FROM docs_memberships WHERE organization_id=%s AND subject=%s',(self.org,'alice'))
        self.assertEqual(self.client.get(self.prefix+'state',headers=self.headers).status_code,404)
    def test_payload_bound_and_cross_origin(self):
        self.assertEqual(self.client.post(self.prefix+'events',headers={**self.headers,'Origin':'https://evil.example'},json=self.event).status_code,403)
        self.assertEqual(self.client.post(self.prefix+'events',headers=self.headers,content=b'x'*(2*1024*1024+1)).status_code,413)
    def test_actor_cannot_be_spoofed(self):
        response=self.client.post(self.prefix+'events',headers=self.headers,json={**self.event,'actor':'bob'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.store.snapshot('shared-name','alice')['audit'][-1]['actor'],'alice')
    def test_full_review_delivery_persists(self):
        result=self.client.post(self.prefix+'events',headers=self.headers,json=self.event).json();item=result['item_id']
        for version,action,data in [(1,'accept',{'change_id':'1'}),(2,'ready',{})]:
            r=self.client.post(self.prefix+'review',headers=self.headers,json={'item_id':item,'version':version,'action':action,'data':data});self.assertEqual(r.status_code,200,r.text)
        r=self.client.post(self.prefix+'approve',headers=self.headers,json={'item_id':item,'version':3,'confirmed':True});self.assertEqual(r.status_code,200,r.text)
        r=self.client.post(self.prefix+'bundle',headers=self.headers,json={'item_id':item});self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.content.startswith(b'PK'))
        self.assertEqual(PostgresStore(self.pool,self.org).snapshot('shared-name','alice')['items'][item]['status'],'delivered')
    def test_failed_capture_cannot_be_overridden_by_comment(self):
        e={**self.event,'requires_capture':True};item=self.store.ingest('shared-name','alice',e)['item_id']
        r=self.client.post(self.prefix+'review',headers=self.headers,json={'item_id':item,'version':1,'action':'answer','data':{'text':'passed'}})
        self.assertEqual(r.status_code,409)

    def test_resumable_setup_and_stale_writes(self):
        body=dict(name='New team',app_url='https://demo.example/app',request_id=str(uuid.uuid4()))
        target=self.client.post('/api/workspaces',headers=self.headers,json=body).json()['workspace']
        self.addCleanup(self.delete_workspace,target.split('/')[0])
        self.assertEqual(self.client.post('/api/workspaces',headers=self.headers,json=body).json()['workspace'],target)
        url='/api/orgs/'+target.split('/')[0]+'/projects/docs/setup'
        edit=dict(revision=0,app_url=body['app_url'],description='Test the reader experience')
        self.assertEqual(self.client.post(url,headers=self.headers,json=edit).status_code,200)
        self.assertEqual(self.client.get(url,headers=self.headers).json()['description'],edit['description'])
        self.assertEqual(self.client.post(url,headers=self.headers,json=edit).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.headers,json={**edit,'app_url':'https://user:secret@demo.example'}).status_code,422)

    def delete_workspace(self,org):
        with self.pool.connection() as db:db.execute('DELETE FROM docs_organizations WHERE id=%s',(org,))

    def test_invitation_rotation_expiry_identity_and_last_admin(self):
        from cqa_artifacts.hosted.onboarding import token_hash
        from dataclasses import replace
        orgurl='/api/orgs/'+self.org
        def invite():
            return self.client.post(orgurl+'/invites',headers=self.headers,json={'subject':'new-user','role':'editor'}).json()['token']
        def accept(client,token):return client.post('/api/invites/accept',headers=self.headers,json={'token':token})
        with TestClient(create_app(replace(self.settings,dev_subject='new-user'),self.pool),base_url=self.settings.origin) as guest:
            old,new=invite(),invite()
            self.assertEqual(accept(guest,old).status_code,404)
            self.assertEqual(accept(self.client,new).status_code,404)
            with self.pool.connection() as db:
                db.execute("UPDATE docs_invites SET expires_at=now()-interval '1 minute' WHERE digest=%s",(token_hash(new),))
            self.assertEqual(accept(guest,new).status_code,410)
            fresh=invite()
            self.assertEqual(accept(guest,fresh).status_code,200)
            self.assertEqual(accept(guest,fresh).status_code,404)
            self.assertEqual(guest.post(orgurl+'/invites',headers=self.headers,json={'subject':'other','role':'admin'}).status_code,403)
            self.assertEqual(self.client.post(orgurl+'/members',headers=self.headers,json={'subject':'alice','role':'editor'}).status_code,409)
            self.assertEqual(self.client.post(orgurl+'/members',headers=self.headers,json={'subject':'new-user','role':'remove'}).status_code,200)
            self.assertEqual(guest.get(self.prefix+'state',headers=self.headers).status_code,404)

    def test_github_scoping_signed_delivery_and_reconnect(self):
        from unittest.mock import patch
        import hmac
        config={'webhook_secret':'s'*32}
        def signed(payload,ident,kind='push',secret=config['webhook_secret']):
            raw=json.dumps(payload).encode()
            return self.client.post(self.prefix+'github/webhook',content=raw,headers={
                'X-GitHub-Event':kind,'X-GitHub-Delivery':ident,'X-Hub-Signature-256':'sha256='+hmac.digest(secret.encode(),raw,'sha256').hex()})
        with patch('cqa_artifacts.hosted.github_intake.binding',return_value=config), patch('cqa_artifacts.hosted.github_intake.github_get',return_value={'repositories':[{'full_name':r,'default_branch':'main'} for r in ('org/product','org/manual')]}):
            scope=dict(revision=0,product_repo='org/product',docs_repo='org/manual',branch='main',docs_root='docs')
            def connect(**changes):
                return self.client.post(self.prefix+'github/connect',json={**scope,**changes},headers=self.headers)
            self.assertEqual(connect(docs_repo='other/private').status_code,403)
            self.assertEqual(connect().status_code,200)
            data=dict(repository={'full_name':'org/product','default_branch':'main'},ref='refs/heads/main',after='1'*40)
            self.assertEqual(signed(data,'invalid',secret='x'*32).status_code,403)
            self.assertEqual(signed({**data,'repository':{'full_name':'other/app'}},'outside').status_code,403)
            self.assertEqual(signed({**data,'ref':'refs/heads/test'},'ignored').json()['status'],'ignored')
            def replay(_):return signed(data,'delivery-1').json()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
                results=list(workers.map(replay,range(4)))
            self.assertEqual(sum(r['status']=='received' for r in results),1)
            self.assertEqual(len({r['item_id'] for r in results}),1)
            merged=dict(repository=data['repository'],action='closed',pull_request=dict(merged=True,base={'ref':'main'},title='Product change',html_url='https://github.com/org/product/pull/1',merge_commit_sha=data['after']))
            self.assertEqual(signed(merged,'delivery-2','pull_request').json()['item_id'],results[0]['item_id'])
            self.assertEqual(signed({**data,'after':'2'*40},'delivery-1').status_code,409)
            state=self.client.get(self.prefix+'setup',headers=self.headers).json()
            self.assertEqual(len(state['deliveries']),2)
            self.assertEqual(state['docs_root'],'docs')
            self.client.post(self.prefix+'github/disconnect',headers=self.headers,json={'revision':1}).raise_for_status()
            self.assertEqual(signed(data,'after-disconnect').status_code,409)
            self.assertEqual(connect(revision=2).status_code,200)

    def test_ordinary_events_cannot_mint_verified_guide_or_source_identity(self):
        for extra in [{'id':'guide:fake'},{'id':'github:team/app@'+'a'*40},{'documentation_destination':{'docs_repo':'team/manual'}}]:
            with self.subTest(extra=extra):
                self.assertEqual(self.client.post(self.prefix+'events',headers=self.headers,json={**self.event,**extra}).status_code,400)

    def test_crawl_reconciliation_prevents_duplicate_starts_and_password_storage(self):
        from unittest.mock import patch
        secret='synthetic-test-login'
        url='https://demo.example/app'
        config=dict(app_url=url,mcp_url='https://example.invalid/mcp',mcp_token='mock',workspace_version_id=1)
        self.client.post(self.prefix+'setup',headers=self.headers,json=dict(app_url=url,description='Explore account navigation',revision=0)).raise_for_status()
        body=dict(revision=1,confirm=True,login_required=True,username='demo',password=secret)
        count=[]
        async def transport(config,args,reserve):
            ident,fresh=reserve()
            if fresh:
                count.append(ident)
                self.assertEqual(args['password'],secret)
                raise TimeoutError
            return ident,None
        with patch('cqa_artifacts.hosted.discovery.binding',return_value=config), patch('cqa_artifacts.hosted.discovery.send_crawl',side_effect=transport):
            self.assertEqual(self.client.post(self.prefix+'discovery',headers=self.headers,json={**body,'confirm':False}).status_code,422)
            first=self.client.post(self.prefix+'discovery',headers=self.headers,json=body).json()
            again=self.client.post(self.prefix+'discovery',headers=self.headers,json=body).json()
            self.assertEqual(first,again)
            self.assertEqual(first['status'],'needs_reconciliation')
            self.assertEqual(len(count),1)
            self.assertNotIn(secret,self.client.get(self.prefix+'setup',headers=self.headers).text)

if __name__=='__main__':unittest.main()
