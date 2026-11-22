"""Synthetic frame provenance tests; real decoding is exercised in live acceptance."""
import unittest
from unittest.mock import patch
from test_journeys import JourneyTests
from cqa_artifacts import core, frames, journeys as j

class FrameTests(unittest.TestCase):
    setUp=JourneyTests.setUp
    attestation=JourneyTests.attestation
    captured=JourneyTests.captured
    def recording(self):
        self.client.step_result['executedResult']={'video_start_time':1000,'video_end_time':2000}
        root=self.captured();mid=core.add_media_bytes(root,b'\x00\x00\x00\x18ftypmp42fixture','video')
        refs=core.load_json(root/'private/artifact-references.json');index=next(i for i,r in enumerate(refs) if r['record']=='cases:100')
        core.write_json(root/'private/media-retrieval.json',[dict(reference_index=index,media_id=mid,kind='video',source_record='cases:100')])
        return root,mid
    def test_unchanged_recording_frame_has_step_and_timestamp_provenance(self):
        root,video=self.recording()
        with patch('cqa_artifacts.frames.frame_bytes',return_value=b'\x89PNG\r\n\x1a\nfixture'):
            row=frames.extract(root,video,200,1500)
            recipe={'steps':[dict(step_result_id=200,media_ids=[row['media_id']])]}
            origin=j.contextqa_media_origins(root,core.manifest(root),recipe)[0]
        self.assertEqual(origin['video_id'],video);self.assertEqual(origin['timestamp_ms'],1500)
    def test_wrong_step_or_time_cannot_create_frame(self):
        root,video=self.recording()
        for step,time in [(999,1500),(200,900),(200,2100)]:
            with self.assertRaises(core.Rejected):frames.extract(root,video,step,time)
    def test_frame_is_redecoded_during_review(self):
        root,video=self.recording()
        with patch('cqa_artifacts.frames.frame_bytes',return_value=b'\x89PNG\r\n\x1a\nfixture'):
            row=frames.extract(root,video,200,1500)
        with patch('cqa_artifacts.frames.frame_bytes',return_value=b'\x89PNG\r\n\x1a\ndifferent'):
            with self.assertRaisesRegex(core.Rejected,'differs'):frames.verified_origin(root,row['media_id'],200)
    def test_video_without_contextqa_receipt_is_rejected(self):
        root,video=self.recording();core.write_json(root/'private/media-retrieval.json',[])
        with self.assertRaisesRegex(core.Rejected,'provenance'):frames.extract(root,video,200,1500)
del JourneyTests
