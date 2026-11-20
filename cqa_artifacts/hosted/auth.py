import os
from dataclasses import dataclass
from urllib.parse import urlsplit
import jwt
from fastapi import HTTPException, Request

@dataclass(frozen=True)
class Settings:
    database_url: str
    origin: str
    mode: str = 'production'
    auth_mode: str = 'oidc'
    issuer: str = ''
    audience: str = ''
    client_id: str = ''
    jwks_url: str = ''
    dev_token: str = ''
    dev_subject: str = 'local-operator'
    scope: str = 'openid profile docs:read docs:write'

    def validate(self):
        if self.mode not in ('development','production') or self.auth_mode not in ('development','oidc'):
            raise ValueError('Unsupported environment or authentication mode')
        if not self.database_url or not self.origin:
            raise ValueError('DATABASE_URL and APP_ORIGIN are required')
        origin = urlsplit(self.origin)
        if origin.path or origin.query or origin.fragment or origin.username or not origin.hostname:
            raise ValueError('APP_ORIGIN must be an origin without a path')
        if self.mode == 'production' and (self.auth_mode != 'oidc' or origin.scheme != 'https'):
            raise ValueError('Production requires OIDC and an HTTPS application origin')
        if self.auth_mode == 'development':
            if self.mode != 'development' or len(self.dev_token) < 32 or origin.hostname not in ('127.0.0.1','localhost'):
                raise ValueError('Development access requires an explicit long token and loopback origin')
        else:
            if not self.client_id or not self.audience:
                raise ValueError('OIDC_CLIENT_ID and OIDC_AUDIENCE are required')
            for url in (self.issuer, self.jwks_url):
                parsed = urlsplit(url)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.fragment:
                    raise ValueError('OIDC issuer and JWKS must be credential-free HTTPS URLs')
        return self

    @classmethod
    def from_env(cls):
        return cls(database_url=os.getenv('DATABASE_URL',''), origin=os.getenv('APP_ORIGIN',''),
                   mode=os.getenv('APP_ENV','production'), auth_mode=os.getenv('AUTH_MODE','oidc'),
                   issuer=os.getenv('OIDC_ISSUER',''), audience=os.getenv('OIDC_AUDIENCE',''),
                   client_id=os.getenv('OIDC_CLIENT_ID',''), jwks_url=os.getenv('OIDC_JWKS_URL',''),
                   dev_token=os.getenv('DEV_ACCESS_TOKEN',''), dev_subject=os.getenv('DEV_SUBJECT','local-operator'),
                   scope=os.getenv('OIDC_SCOPE','openid profile docs:read docs:write')).validate()

class Authenticator:
    def __init__(self, settings):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(settings.jwks_url, timeout=5) if settings.auth_mode == 'oidc' else None

    def __call__(self, request: Request):
        import hmac
        header = request.headers.get('authorization','')
        if not header.startswith('Bearer ') or len(header)>16384:
            raise HTTPException(401,'Sign in to continue',headers={'WWW-Authenticate':'Bearer'})
        token = header[7:]
        if self.settings.auth_mode == 'development':
            if not hmac.compare_digest(token,self.settings.dev_token):
                raise HTTPException(401,'Invalid development session')
            return self.settings.dev_subject
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token,key,algorithms=['RS256'],audience=self.settings.audience,
                                issuer=self.settings.issuer,options={'require':['exp','iat','iss','aud','sub']},leeway=30)
            subject = claims['sub']
            if not isinstance(subject,str) or not 0<len(subject)<=200:
                raise ValueError('Invalid subject')
            required = 'docs:read' if request.method in ('GET','HEAD') else 'docs:write'
            if required not in claims.get('scope','').split():
                raise HTTPException(403,'Required API scope missing')
            return subject
        except (jwt.PyJWTError, ValueError, TypeError):
            raise HTTPException(401,'Session invalid or expired',headers={'WWW-Authenticate':'Bearer'}) from None
