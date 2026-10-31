"""Explicit selected-artifact retrieval. Never send the ContextQA bearer to storage."""
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from . import core

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise core.Rejected('Artifact redirect refused; review the direct storage reference')


def fetch_media(root, index, kind, allowed_host, *, transport=None, resolver=socket.getaddrinfo):
    root = Path(root)
    references = core.load_json(root/'private/artifact-references.json')
    if type(index) is not int or not isinstance(references,list) or not 0 <= index < len(references):
        raise core.Rejected('Select an existing artifact reference index')
    if kind not in ('screenshot','video'):
        raise core.Rejected('Only screenshot or video retrieval is supported')
    reference=references[index]
    url=reference.get('url') if isinstance(reference,dict) else None
    if not isinstance(url,str) or len(url)>16000 or any(ord(c)<33 for c in url):
        raise core.Rejected('Invalid artifact reference')
    try:
        p=urllib.parse.urlsplit(url)
        if p.scheme!='https' or p.hostname!=allowed_host or p.username or p.password or p.port not in (None,443) or p.fragment:
            raise ValueError()
        if not allowed_host or not all(c.isalnum() or c in '.-' for c in allowed_host) or '.' not in allowed_host:
            raise ValueError()
        addresses=resolver(allowed_host,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError()
    except (ValueError,OSError):
        raise core.Rejected('Artifact must use the explicitly reviewed public HTTPS host') from None
    request=urllib.request.Request(url,headers={'Accept':'image/png,image/jpeg,image/webp' if kind=='screenshot' else 'video/mp4,video/webm'})
    # Separate no-proxy/no-redirect client. No API token, cookie jar or environment auth.
    try:
        if transport:
            payload=transport(request,20,core.MAX_MEDIA)
        else:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            with opener.open(request,timeout=20) as response:
                payload=response.read(core.MAX_MEDIA+1)
        if not isinstance(payload,bytes) or len(payload)>core.MAX_MEDIA:
            raise core.Rejected('Artifact exceeds media limit')
        media_id=core.add_media_bytes(root,payload,kind)
    except Exception:
        raise core.Rejected('Artifact retrieval failed; no retry, token forwarding or automatic attachment occurred') from None
    receipts_path=root/'private/media-retrieval.json'
    receipts=core.load_json(receipts_path) if receipts_path.exists() else []
    receipts.append({'reference_index':index,'media_id':media_id,'kind':kind,'source_record':reference.get('record'),'review_required':True})
    core.write_json(receipts_path,receipts)
    return {'media_id':media_id,'kind':kind,'downloaded':True,'attached':False,'review_required':True}
