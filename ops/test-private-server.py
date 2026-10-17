"""Authentication regression tests use a disposable test day, never the owner's birthday."""
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

class PrivateServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        (cls.root/'thoughts').mkdir()
        (cls.root/'thoughts/index.html').write_text('PRIVATE_FIXTURE_CONTENT')
        (cls.root/'thoughts/photo.jpg').write_bytes(b'PRIVATE_IMAGE')
        (cls.root/'session.key').write_bytes(b'test-only-session-secret-not-production')
        salt=b'fixture-salt'
        (cls.root/'birthday.json').write_text(json.dumps({'salt':salt.hex(),'iterations':1000,'digest':hashlib.pbkdf2_hmac('sha256',b'17',salt,1000).hex()}))
        os.environ['PRIVATE_CONFIG']=str(cls.root)
        os.environ['PRIVATE_ROOT']=str(cls.root)
        spec=importlib.util.spec_from_file_location('private_service',Path(__file__).with_name('private-server.py'))
        cls.service=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.service)
        cls.http=cls.service.http.server.ThreadingHTTPServer(('127.0.0.1',0),cls.service.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def setUp(self):
        self.service.failures.clear();self.service.global_failures.clear()
    def request(self,path='/thoughts/',method='GET',body=None,cookie=None,origin='https://bd3pzh.top'):
        connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=5)
        headers={'Host':'bd3pzh.top','Origin':origin}
        if cookie:headers['Cookie']=cookie
        connection.request(method,path,body=body,headers=headers)
        response=connection.getresponse();result=(response.status,dict(response.getheaders()),response.read());connection.close();return result
    def login(self,day='17'):
        return self.request('/_private/login','POST','birthday='+day)
    def test_unauthenticated_content_and_assets_redirect(self):
        for path in ('/thoughts/','/thoughts/photo.jpg','/thoughts/example/'):
            status,headers,body=self.request(path)
            self.assertEqual(status,303);self.assertNotIn(b'PRIVATE_',body)
            self.assertTrue(headers['Location'].startswith('/categories/personal-thoughts/'))
    def test_correct_day_and_secure_session(self):
        status,headers,_=self.login();self.assertEqual(status,303)
        cookie=headers['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie);self.assertIn('SameSite=Lax',cookie)
        status,headers,body=self.request(cookie=cookie.split(';')[0]);self.assertEqual(status,200);self.assertEqual(body,b'PRIVATE_FIXTURE_CONTENT');self.assertIn('no-store',headers['Cache-Control'])
    def test_incorrect_and_invalid_days(self):
        for day in ('18','0','31','abc','20261017'):
            status,headers,_=self.login(day);self.assertEqual(status,303);self.assertNotIn('Set-Cookie',headers)
    def test_rate_limit_including_correct_day(self):
        for _ in range(5):self.login('18')
        _,headers,_=self.login();self.assertIn('error=limited',headers['Location']);self.assertNotIn('Set-Cookie',headers)
    def test_forged_cookie_and_path_traversal(self):
        status,_,_=self.request(cookie='__Secure-thoughts=9999999999.x.fake');self.assertEqual(status,303)
        _,headers,_=self.login();cookie=headers['Set-Cookie'].split(';')[0]
        status,_,_=self.request('/thoughts/../birthday.json',cookie=cookie);self.assertEqual(status,404)
    def test_cross_origin_and_logout(self):
        status,_,_=self.request('/_private/login','POST','birthday=17',origin='https://unrelated.example');self.assertEqual(status,403)
        status,headers,_=self.request('/_private/logout','POST','');self.assertEqual(status,303);self.assertIn('Max-Age=0',headers['Set-Cookie'])
    def test_status_and_exact_day_normalization(self):
        self.assertEqual(self.request('/_private/status')[0],401)
        self.assertEqual(self.service.normalize_day('09'),'9')
        self.assertIsNone(self.service.normalize_day('9x'))

if __name__=='__main__':unittest.main(verbosity=2)
