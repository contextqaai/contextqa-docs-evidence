"""Extract unchanged frames from a downloaded ContextQA recording, with provenance."""
import argparse
import json
import subprocess
from pathlib import Path
from . import core


def frame_bytes(video, timestamp_ms):
    if type(timestamp_ms) is not int or not 0<=timestamp_ms<=86400000:
        raise core.Rejected('Use a bounded recording timestamp in milliseconds')
    try:
        result=subprocess.run(['ffmpeg','-v','error','-ss',str(timestamp_ms/1000),'-i',str(video),
            '-frames:v','1','-f','image2pipe','-vcodec','png','-'],capture_output=True,timeout=30)
    except (OSError,subprocess.TimeoutExpired):raise core.Rejected('Frame extraction requires local ffmpeg') from None
    if result.returncode or not result.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
        raise core.Rejected('Recording has no decodable frame at that timestamp')
    return result.stdout


def validate_source(root, video_id, step_result_id, timestamp_ms):
    root=Path(root);data=core.manifest(root)
    video=next((m for m in data['media'] if m['id']==video_id and m['kind']=='video'),None)
    step=next((s for s in data['steps'] if s['step_result_id']==step_result_id),None)
    if not video or not step:raise core.Rejected('Frame needs a captured step and downloaded recording')
    raw=core.regular_file(core.asset_file(root,video['path']))
    if core.digest(raw)!=video_id:raise core.Rejected('Recording bytes changed')
    refs=core.load_json(root/'private/artifact-references.json')
    receipts=core.load_json(root/'private/media-retrieval.json')
    matched=None
    for receipt in receipts:
        index=receipt.get('reference_index')
        if receipt.get('media_id')!=video_id or receipt.get('kind')!='video' or type(index) is not int or not 0<=index<len(refs):continue
        ref=refs[index]
        if ref.get('record') not in {'cases:'+str(step.get('case_result_id')),'steps:'+str(step_result_id)}:continue
        if receipt.get('source_record')!=ref['record'] or ref.get('field','').split('/')[0] not in ('screenRecordingUrl','screenRecordings'):continue
        matched=receipt;break
    if not matched:raise core.Rejected('Recording has no matching ContextQA artifact provenance')
    results=core.load_json(root/'private/contextqa-results.json')
    detail=next((s for s in results['steps'] if s['id']==step_result_id),{})
    timing=detail.get('executedResult') or {}
    start,end=timing.get('video_start_time'),timing.get('video_end_time')
    if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or not start<=timestamp_ms<=end:
        raise core.Rejected('Frame timestamp must fall within the ContextQA step recording interval')
    return video,matched


def extract(root,video_id,step_result_id,timestamp_ms):
    root=Path(root);video,source=validate_source(root,video_id,step_result_id,timestamp_ms)
    raw=frame_bytes(core.asset_file(root,video['path']),timestamp_ms)
    mid=core.add_media_bytes(root,raw,'screenshot')
    path=root/'private/frame-derivations.json';rows=core.load_json(path) if path.exists() else []
    row=dict(media_id=mid,video_id=video_id,step_result_id=step_result_id,timestamp_ms=timestamp_ms,
             reference_index=source['reference_index'],source_record=source['source_record'],method='contextqa-recording-frame-v1')
    if row not in rows:rows.append(row);core.write_json(path,rows)
    return row


def verified_origin(root,mid,step_result_id):
    root=Path(root);path=root/'private/frame-derivations.json'
    if not path.exists():return None
    row=next((r for r in core.load_json(path) if r.get('media_id')==mid and r.get('step_result_id')==step_result_id),None)
    if not row or row.get('method')!='contextqa-recording-frame-v1':return None
    video,source=validate_source(root,row['video_id'],step_result_id,row['timestamp_ms'])
    if row['reference_index']!=source['reference_index'] or row['source_record']!=source['source_record']:
        raise core.Rejected('Frame provenance changed')
    if core.digest(frame_bytes(core.asset_file(root,video['path']),row['timestamp_ms']))!=mid:
        raise core.Rejected('Frame differs from its ContextQA recording')
    return dict(row,kind='screenshot')


def cli():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',required=True);p.add_argument('--video-id',required=True);p.add_argument('--step-result-id',required=True,type=int);p.add_argument('--timestamp-ms',required=True,type=int)
    a=p.parse_args();print(json.dumps(extract(a.capture,a.video_id,a.step_result_id,a.timestamp_ms),indent=2))
if __name__=='__main__':cli()
