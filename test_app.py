"""Local integration tests: python -m unittest -v test_app.py"""
import http.cookiejar
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
import server

class Client:
    def __init__(self, base):
        self.base=base
        self.cookies=http.cookiejar.CookieJar()
        self.opener=build_opener(HTTPCookieProcessor(self.cookies))
        self.csrf=''
    def req(self,path,data=None,method='GET',csrf=True,origin=None):
        headers={'Accept':'application/json'}
        if data is not None:headers['Content-Type']='application/json'
        if csrf and self.csrf and method!='GET':headers['X-CSRF-Token']=self.csrf
        if origin:headers['Origin']=origin
        request=Request(self.base+path, data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
        try:
            with self.opener.open(request) as r:
                raw=r.read();return r.status, json.loads(raw) if r.headers.get('Content-Type','').startswith('application/json') else raw
        except HTTPError as e:
            return e.code,json.loads(e.read())
    def register(self,email,pharmacy,demo=False):
        status,data=self.req('/api/register',{'email':email,'full_name':'Kiểm thử Nhà thuốc','pharmacy_name':pharmacy,'password':'securepass-2026','password_confirm':'securepass-2026','accept':True,'demo':demo},'POST')
        if status!=201:raise AssertionError((status,data))
        self.get_me()
    def login(self,email,password='securepass-2026'):
        status,data=self.req('/api/login',{'email':email,'password':password},'POST')
        if status!=200:raise AssertionError((status,data))
        self.get_me()
    def get_me(self):
        status,data=self.req('/api/me');self.csrf=data.get('csrf','');return status,data

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();server.DB_FILE=Path(cls.tmp.name)/'test.sqlite3'
        server.init_database();cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join(timeout=4);cls.tmp.cleanup()
    def setUp(self):
        server.RATE.clear()

    def test_01_registration_and_login(self):
        a=Client(self.base)
        self.assertEqual(a.req('/api/products')[0],401)
        self.assertEqual(a.req('/api/register',{'email':'a@demo.vn','pharmacy_name':'Nhà thuốc A','full_name':'A Admin','password':'securepass-2026','password_confirm':'securepass-2026','accept':False},'POST')[0],400)
        a.register('first@demo.vn','Nhà thuốc A',demo=True)
        status,me=a.get_me();self.assertEqual(status,200);self.assertEqual(me['user']['pharmacy_name'],'Nhà thuốc A');self.assertTrue(me['user']['demo'])
        self.assertEqual(len(a.req('/api/products')[1]['products']),6)
        self.assertEqual(a.req('/api/products',{'name':'X'},'POST',csrf=False)[0],403)
        self.assertEqual(a.req('/api/products',{'name':'X'},'POST',origin='https://attacker.test')[0],403)
        self.assertEqual(a.req('/server.py')[0],404)
        self.assertEqual(a.req('/pharmavision.sqlite3')[0],404)
        self.assertEqual(a.req('/api/logout',method='POST')[0],200)
        self.assertEqual(a.req('/api/products')[0],401)
        self.assertEqual(a.req('/api/login',{'email':'first@demo.vn','password':'wrong'},'POST')[0],401)
        a.login('first@demo.vn')
        self.assertEqual(a.req('/api/products')[0],200)
    def test_02_tenant_isolation_and_fefo(self):
        a=Client(self.base);a.register('tenant-a@test.vn','Tenant A')
        b=Client(self.base);b.register('tenant-b@test.vn','Tenant B')
        self.assertEqual(len(a.req('/api/products')[1]['products']),0)
        code,r=a.req('/api/products',{'name':'Test Medicine','active':'Sample','strength':'10mg','price':10000,'reorder_point':10},'POST');self.assertEqual(code,201);pid=r['id']
        self.assertEqual(len(b.req('/api/products')[1]['products']),0)
        self.assertEqual(b.req('/api/stock/import',{'product_id':pid,'qty':100,'lot':'A1','expires':'2028-06-30'},'POST')[0],404)
        # insert two batches, earliest expiry must be consumed first
        self.assertEqual(a.req('/api/stock/import',{'product_id':pid,'qty':10,'lot':'A-NEW','expires':'2028-06-30','cost':900},'POST')[0],200)
        self.assertEqual(a.req('/api/stock/import',{'product_id':pid,'qty':5,'lot':'A-OLD','expires':'2027-06-30'},'POST')[0],200)
        self.assertEqual(a.req('/api/sales',{'pharmacist_verified':True,'items':[{'product_id':pid,'qty':100}]},'POST')[0],409)
        self.assertEqual(a.req('/api/products')[1]['products'][0]['stock'],15)
        code,sale=a.req('/api/sales',{'pharmacist_verified':True,'items':[{'product_id':pid,'qty':7}]},'POST')
        self.assertEqual(code,201);self.assertEqual(sale['total'],70000)
        lots={x['lot']:x['qty'] for x in a.req('/api/products')[1]['products'][0]['batches']}
        self.assertEqual(lots['A-OLD'],0);self.assertEqual(lots['A-NEW'],8)
        self.assertEqual(a.req('/api/sales')[1]['sales'][0]['lines'][0]['qty'],5)
        self.assertEqual(len(b.req('/api/sales')[1]['sales']),0)
        # register recall in one tenant; hold must not affect other
        code,r=a.req('/api/recalls',{'lot':'A-NEW','reason':'Thông báo thu hồi kiểm thử','source':'Nhà phân phối'},'POST')
        self.assertEqual(code,201);self.assertEqual(r['matched'],1)
        self.assertEqual(a.req('/api/sales',{'pharmacist_verified':True,'items':[{'product_id':pid,'qty':1}]},'POST')[0],409)
        self.assertEqual(a.req('/api/stock/hold',{'batch_id':a.req('/api/products')[1]['products'][0]['batches'][1]['id'],'hold':False,'reason':'Thử mở lại'},'POST')[0],409)
        self.assertEqual(a.req('/api/dashboard')[1]['metrics']['products'],1)
        self.assertEqual(b.req('/api/dashboard')[1]['metrics']['products'],0)
    def test_03_staff_permissions_and_data_consent(self):
        a=Client(self.base);a.register('tenant-c@test.vn','Tenant C')
        self.assertEqual(a.req('/api/users',{'email':'staff-c@test.vn','full_name':'Nhân viên C','password':'staffpass-2026','role':'staff'},'POST')[0],201)
        staff=Client(self.base);staff.login('staff-c@test.vn','staffpass-2026')
        self.assertEqual(staff.req('/api/users')[0],403)
        self.assertEqual(staff.req('/api/recalls',{'lot':'A','reason':'Some reason','source':'Some source'},'POST')[0],403)
        self.assertEqual(staff.req('/api/customers',{'name':'Bệnh nhân thử','allergies':'Chưa rõ','consent':False},'POST')[0],400)
        status,result=staff.req('/api/customers',{'name':'Khách demo','phone':'0900000000','consent':True,'allergies':'Thông tin mô phỏng'},'POST')
        self.assertEqual(status,201)
        self.assertEqual(staff.req('/api/customers/'+str(result['id']),method='DELETE')[0],403)
        self.assertEqual(a.req('/api/customers/'+str(result['id']),method='DELETE')[0],200)
        self.assertEqual(a.req('/api/customers')[1]['customers'],[])
        self.assertEqual(a.req('/api/password',{'old_password':'bad','new_password':'newsecurepass-2026'},'POST')[0],403)
        self.assertEqual(a.req('/api/password',{'old_password':'securepass-2026','new_password':'newsecurepass-2026'},'POST')[0],200)
        self.assertEqual(a.req('/api/forecast')[0],200)
        self.assertEqual(a.req('/api/copilot',{'question':'Paracetamol'},'POST')[0],200)
    def test_04_rx_checks_and_expired(self):
        a=Client(self.base);a.register('tenant-d@test.vn','Tenant D')
        _,p=a.req('/api/products',{'name':'Thuốc Rx Demo','requires_rx':True,'price':20000},'POST');pid=p['id']
        a.req('/api/stock/import',{'product_id':pid,'lot':'EXPIRED','expires':'2022-04-01','qty':20},'POST')
        self.assertEqual(a.req('/api/sales',{'items':[{'product_id':pid,'qty':1}],'pharmacist_verified':True,'rx_verified':True,'prescription_code':'P-1'},'POST')[0],409)
        a.req('/api/stock/import',{'product_id':pid,'lot':'VALID','expires':'2028-04-01','qty':20},'POST')
        self.assertEqual(a.req('/api/sales',{'items':[{'product_id':pid,'qty':1}],'pharmacist_verified':True},'POST')[0],400)
        self.assertEqual(a.req('/api/sales',{'items':[{'product_id':pid,'qty':1}],'pharmacist_verified':True,'rx_verified':True},'POST')[0],400)
        self.assertEqual(a.req('/api/sales',{'items':[{'product_id':pid,'qty':1}],'pharmacist_verified':True,'rx_verified':True,'prescription_code':'P-1'},'POST')[0],201)
    def test_05_static(self):
        c=Client(self.base)
        for path in ('/','/login','/register','/app','/workspace.js','/styles.css','/mobile.css','/mobile.js','/app.css'):
            status,blob=c.req(path)
            self.assertEqual(status,200)
            self.assertGreater(len(blob),50)

    def test_06_mobile_assets_and_navigation(self):
        c=Client(self.base)
        for path in ('/mobile.css','/mobile.js'):
            status,blob=c.req(path)
            self.assertEqual(status,200)
            self.assertGreater(len(blob),200)
        status,html=c.req('/app')
        self.assertEqual(status,200)
        html=html.decode('utf-8')
        self.assertIn('id="mobileBottomNav"',html)
        self.assertIn('data-mobile-page="sales"',html)
        self.assertIn('viewport-fit=cover',html)

    def test_07_design_system_assets(self):
        client = Client(self.base)
        for path in ('/design.css','/design.js'):
            status, payload = client.req(path)
            self.assertEqual(status, 200)
            self.assertGreater(len(payload), 500)
        for path in ('/','/login','/register','/app'):
            status, payload = client.req(path)
            self.assertEqual(status, 200)
            html = payload.decode('utf-8')
            self.assertIn('href="/app.css"', html)
            self.assertIn('src="/design.js"', html)
        status, payload = client.req('/app')
        html = payload.decode('utf-8')
        self.assertIn('id="headerQuickSearch"', html)
        self.assertIn('id="headerQuickSale"', html)

    def test_08_vietnamese_font_and_svg_icons(self):
        client = Client(self.base)
        for path in ('/typography.css','/icons.js'):
            status, payload = client.req(path)
            self.assertEqual(status, 200)
            self.assertGreater(len(payload), 500)
        status, sheet = client.req('/typography.css')
        self.assertIn(b'--pv-font:Arial', sheet)
        status, icons = client.req('/icons.js')
        self.assertIn(b'createElementNS', icons)
        for path in ('/','/login','/register','/app'):
            status, response = client.req(path)
            self.assertEqual(status, 200)
            html = response.decode('utf-8')
            self.assertIn('charset="UTF-8"', html.lower().replace('charset="utf-8"','charset="UTF-8"'))
            self.assertNotIn('fonts.googleapis.com', html)
            self.assertIn('href="/app.css"', html)
            self.assertIn('src="/icons.js"', html)

    def test_09_system_font_without_google_dependency(self):
        client = Client(self.base)
        for path in ('/','/login','/register','/app'):
            status, response = client.req(path)
            self.assertEqual(status, 200)
            html = response.decode('utf-8')
            self.assertNotIn('fonts.googleapis.com', html)
            self.assertNotIn('fonts.gstatic.com', html)
            self.assertIn('href="/app.css"', html)
        status, response = client.req('/typography.css')
        self.assertEqual(status, 200)
        css = response.decode('utf-8')
        self.assertIn("--pv-font:Arial", css)
        self.assertIn(".section-kicker,.section-kicker.light", css)
        self.assertNotIn("'Be Vietnam Pro'", css)

    def test_10_unified_stylesheet_and_asset_pipeline(self):
        import importlib.util
        builder = Path(__file__).resolve().parent / 'tools' / 'build_assets.py'
        spec = importlib.util.spec_from_file_location('pharmora_css_build', builder)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = module.build_css()
        bundled = (Path(__file__).resolve().parent / 'static' / 'app.css').read_text(encoding='utf-8')
        self.assertEqual(bundled, expected)
        self.assertIn('font-family:Arial', bundled)
        self.assertIn('.pv-sale-no-results', bundled)
        self.assertIn('.section-kicker', bundled)
        client = Client(self.base)
        status, response = client.req('/app.css')
        self.assertEqual(status, 200)
        self.assertEqual(response.decode('utf-8'), bundled)
        for path in ('/','/login','/register','/app'):
            status, payload = client.req(path)
            self.assertEqual(status, 200)
            html = payload.decode('utf-8')
            self.assertEqual(html.count('rel="stylesheet"'), 1)
            self.assertIn('href="/app.css"', html)
        status, response = client.req('/app')
        html = response.decode('utf-8')
        self.assertIn('id="mobileBottomNav"', html)
        self.assertIn('id="headerQuickSearch"', html)

if __name__=='__main__':unittest.main()
