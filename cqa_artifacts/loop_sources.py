"""Offline source normalization; GitHub payload authenticity checked before parsing."""
import hashlib
import hmac
import json
from .core import Rejected
from .loop import text, strings


def github_event(raw, signature, secret, repository, delivery):
    if not isinstance(raw, bytes) or len(raw)>2*1024*1024 or not isinstance(secret,str) or len(secret)<24:
        raise Rejected('Invalid webhook input or secret (minimum 24 characters)')
    expected='sha256='+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    if not isinstance(signature,str) or not hmac.compare_digest(expected,signature):
        raise Rejected('Webhook signature mismatch')
    data=json.loads(raw)
    if data.get('repository',{}).get('full_name')!=repository:
        raise Rejected('Repository is outside project scope')
    pr=data.get('pull_request',{})
    if data.get('action')!='closed' or pr.get('merged') is not True or pr.get('base',{}).get('ref')!=data['repository'].get('default_branch'):
        raise Rejected('Only default-branch merged pull requests are eligible')
    return dict(id='github:'+text(delivery,'delivery',200),source='github',title=text(pr.get('title'),'PR title'),
        text=pr.get('body') or 'Merged product change; inspect source before drafting.',source_url=pr['html_url'],
        revision=pr.get('merge_commit_sha'),repository=repository,
        changed_paths=[],note='GitHub PR webhook does not contain changed files. Supply reviewed file paths separately.')


def transcript_event(identifier,title,transcript,segments,source_url):
    """Accept an operator-reviewed transcript and explicitly selected feature segments.

    Does not download videos, transcribe audio, select frames or invent UI steps.
    """
    text(transcript,'transcript',200000)
    if not isinstance(segments,list) or not 1<=len(segments)<=50:
        raise Rejected('Provide 1–50 reviewed feature segments')
    events=[]
    for n,segment in enumerate(segments):
        if not isinstance(segment,dict):
            raise Rejected('Invalid segment')
        start,end=segment.get('start_seconds'),segment.get('end_seconds')
        if type(start) not in (int,float) or type(end) not in (int,float) or not 0<=start<end<=86400:
            raise Rejected('Invalid segment timestamps')
        quote=text(segment.get('excerpt'),'transcript excerpt',20000)
        if quote not in transcript:
            raise Rejected('Segment excerpt must occur in supplied transcript')
        events.append(dict(id=f'{identifier}:{n}',source='video',title=text(segment.get('title'),'feature title'),text=quote,
            source_url=source_url,video_title=title,start_seconds=start,end_seconds=end,
            edits=segment.get('edits',[]),module_ids=strings(segment.get('module_ids',[]),'module_ids')))
    return events
