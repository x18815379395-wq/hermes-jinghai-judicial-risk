import importlib.util
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("jinghai_judicial.py")
spec = importlib.util.spec_from_file_location("jinghai_judicial", MODULE_PATH)
jh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jh)

class Handler(BaseHTTPRequestHandler):
    calls=0; mode="success"; last_headers={}; last_body={}; last_path=""
    def log_message(self,*args): pass
    def do_POST(self):
        type(self).calls+=1; type(self).last_headers=dict(self.headers); type(self).last_path=self.path
        raw=self.rfile.read(int(self.headers.get("Content-Length","0"))); type(self).last_body=json.loads(raw.decode("utf-8"))
        if self.mode=="retry" and self.calls<2: self.send_response(429); body={"errcode":429,"errmsg":"rate","success":False}
        elif self.mode=="business_error": self.send_response(200); body={"status":403,"message":"未授权","success":False}
        else: self.send_response(200); self.send_header("X-Jinghai-Request-Id","req-test"); body={"status":200,"success":True,"data":{"total":1,"records":[{"caseNumber":"案号1"}]}}
        data=json.dumps(body,ensure_ascii=False).encode("utf-8"); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)

class JinghaiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler); cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start(); cls.base=f"http://127.0.0.1:{cls.server.server_port}"
    @classmethod
    def tearDownClass(cls): cls.server.shutdown(); cls.server.server_close()
    def setUp(self): Handler.calls=0; Handler.mode="success"; os.environ["JINGHAI_APP_ID"]="test-app"; os.environ["JINGHAI_API_KEY"]="test-key"
    def tearDown(self): os.environ.pop("JINGHAI_APP_ID",None); os.environ.pop("JINGHAI_API_KEY",None)
    def test_missing_credentials_is_distinct_error(self):
        os.environ.pop("JINGHAI_API_KEY")
        with self.assertRaises(jh.JinghaiError) as cm: jh.call_api("测试企业",base_url=self.base)
        self.assertEqual(cm.exception.kind,"missing_credentials"); self.assertEqual(Handler.calls,0)
    def test_success_encodes_company_and_sends_headers(self):
        result=jh.call_api("深圳 腾讯/测试有限公司",tag=0,page_size=20,base_url=self.base)
        self.assertEqual(result["query_status"],"success"); self.assertEqual(result["total"],1); self.assertEqual(result["request_id"],"req-test"); self.assertIn("%2F",Handler.last_path); self.assertEqual(Handler.last_headers["X-Jinghai-App-Id"],"test-app"); self.assertEqual(Handler.last_body,{"tag":0,"pageIndex":1,"pageSize":20})
    @patch.object(jh.time,"sleep",lambda _:None)
    @patch.object(jh.random,"random",lambda:0)
    def test_429_retries_then_succeeds(self):
        Handler.mode="retry"; result=jh.call_api("测试企业",max_retries=2,base_url=self.base); self.assertEqual(result["query_status"],"success"); self.assertEqual(Handler.calls,2)
    def test_business_error_never_becomes_no_records(self):
        Handler.mode="business_error"
        with self.assertRaises(jh.JinghaiError) as cm: jh.call_api("测试企业",max_retries=0,base_url=self.base)
        self.assertEqual(cm.exception.kind,"business_error"); self.assertEqual(cm.exception.business_code,403)
    def test_batch_real_call_does_not_forward_interval(self):
        result=jh.batch_query(["企业甲","企业乙"],interval=0,base_url=self.base,max_retries=0); self.assertEqual(result["summary"]["success"],2); self.assertEqual(result["summary"]["errors"],0)
    @patch.object(jh.time,"sleep",lambda _:None)
    def test_batch_deduplicates_and_separates_errors(self):
        def fake(name,**kwargs):
            if name=="坏企业": raise jh.JinghaiError("network_error","失败")
            return {"company":name,"query_status":"success","records":[]}
        with patch.object(jh,"call_api",fake): result=jh.batch_query(["好企业","好企业","坏企业"],interval=0)
        self.assertEqual(result["summary"],{"companies":2,"success":1,"errors":1,"with_records":0}); self.assertEqual(result["results"][1]["query_status"],"error")

if __name__=="__main__": unittest.main(verbosity=2)
