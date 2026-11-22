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
        with cls.pool.connection() as db:db.execute((ROOT/'migrations/001_hosted.sql').read_text())
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

if __name__=='__main__':unittest.main()
