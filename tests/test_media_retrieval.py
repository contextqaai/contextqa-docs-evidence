from pathlib import Path
import tempfile
import unittest
from cqa_artifacts import core
from cqa_artifacts.media import fetch_media

class MediaRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.w=Path(self.t.name)/'w';core.init(self.w,'Demo')
        core.write_json(self.w/'private/artifact-references.json',[{'record':'steps:12','url':'https://media.example.com/frame.png?signature=private'}])
        self.resolve=lambda *a,**k:[(2,1,6,'',('8.8.8.8',443))]
    def test_no_auth_or_signed_url_export_and_no_auto_attachment(self):
        def transport(req,timeout,limit):
            self.assertIsNone(req.get_header('Authorization'))
            self.assertIsNone(req.get_header('Cookie'))
            return b'\x89PNG\r\n\x1a\nsynthetic-fixture'
        r=fetch_media(self.w,0,'screenshot','media.example.com',transport=transport,resolver=self.resolve)
        self.assertTrue(r['downloaded']);self.assertFalse(r['attached'])
        self.assertNotIn('signature',str(core.manifest(self.w)))
    def test_unapproved_or_private_host_rejected_before_transport(self):
        def bad(*a):raise AssertionError('must not fetch')
        with self.assertRaises(core.Rejected):fetch_media(self.w,0,'screenshot','other.example.com',transport=bad,resolver=self.resolve)
        resolve=lambda *a,**k:[(2,1,6,'',('127.0.0.1',443))]
        with self.assertRaises(core.Rejected):fetch_media(self.w,0,'screenshot','media.example.com',transport=bad,resolver=resolve)
    def test_error_body_and_signed_url_are_not_exposed(self):
        def fail(*a):raise RuntimeError('secret provider response signature=private')
        with self.assertRaises(core.Rejected) as e:fetch_media(self.w,0,'screenshot','media.example.com',transport=fail,resolver=self.resolve)
        self.assertNotIn('signature',str(e.exception))
    def test_html_rejected_as_media(self):
        with self.assertRaises(core.Rejected):fetch_media(self.w,0,'screenshot','media.example.com',transport=lambda *a:b'<html>login</html>',resolver=self.resolve)
