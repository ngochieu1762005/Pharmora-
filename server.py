"""PharmaVision AI local multi-tenant demonstration server.

Python standard library only. Security/compliance verification required before real deployment.
No online clinical or regulatory integrations are implied.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import date, timedelta, datetime
import hashlib
import hmac
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'static'
DB_FILE = Path(os.environ.get('PHARMAVISION_DB', str(ROOT / 'pharmavision.sqlite3'))).resolve()
SESSION_AGE = 12 * 3600
COOKIE_NAME = 'pv_session'
LOCK = threading.RLock()
RATE = {}
EMAIL_RE = re.compile(r'^[^\s@]{1,64}@[^\s@]{1,200}\.[^\s@]{2,}$')
ALLOWED_STATIC = {'/': 'index.html', '/index.html': 'index.html', '/login': 'login.html', '/register': 'register.html', '/app': 'workspace.html',
                  '/styles.css': 'styles.css', '/site.js': 'site.js', '/workspace.js': 'workspace.js',
                  '/mobile.css': 'mobile.css', '/mobile.js': 'mobile.js',
                  '/design.css': 'design.css', '/design.js': 'design.js',
                  '/typography.css': 'typography.css', '/icons.js': 'icons.js',
                  '/app.css': 'app.css'}


@contextmanager
def database():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=15000')
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    with database() as c:
        c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS pharmacies (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL, demo INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE, full_name TEXT NOT NULL,
                pass_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','staff')),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                csrf TEXT NOT NULL, expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                name TEXT NOT NULL, active TEXT NOT NULL DEFAULT '', strength TEXT NOT NULL DEFAULT '',
                form TEXT NOT NULL DEFAULT '', unit TEXT NOT NULL DEFAULT 'hộp', barcode TEXT NOT NULL DEFAULT '',
                price INTEGER NOT NULL DEFAULT 0 CHECK(price>=0), reorder_point INTEGER NOT NULL DEFAULT 20 CHECK(reorder_point>=0),
                requires_rx INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_products_ph ON products(pharmacy_id);
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                lot TEXT NOT NULL, expires TEXT NOT NULL, qty INTEGER NOT NULL DEFAULT 0 CHECK(qty>=0),
                supplier TEXT NOT NULL DEFAULT '', cost INTEGER NOT NULL DEFAULT 0 CHECK(cost>=0),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','quarantine')),
                received_at TEXT NOT NULL, UNIQUE(pharmacy_id,product_id,lot)
            );
            CREATE INDEX IF NOT EXISTS idx_batches_ph ON batches(pharmacy_id,product_id,expires);
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', consent INTEGER NOT NULL DEFAULT 0,
                consent_at TEXT, allergies TEXT NOT NULL DEFAULT '', reported_meds TEXT NOT NULL DEFAULT '',
                care_notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
                total INTEGER NOT NULL CHECK(total>=0), created_at TEXT NOT NULL,
                verified_by INTEGER NOT NULL REFERENCES users(id), prescription_code TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS sale_lines (
                id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id), batch_id INTEGER NOT NULL REFERENCES batches(id),
                qty INTEGER NOT NULL CHECK(qty>0), unit_price INTEGER NOT NULL CHECK(unit_price>=0)
            );
            CREATE TABLE IF NOT EXISTS stock_moves (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                batch_id INTEGER NOT NULL REFERENCES batches(id), change_qty INTEGER NOT NULL,
                kind TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', actor_id INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recalls (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id), lot TEXT NOT NULL, reason TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'Nhập thủ công', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id),
                actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL, detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        ''')


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def hash_password(pw):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pw.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
    return 'scrypt$'+base64.b64encode(salt).decode()+'$'+base64.b64encode(digest).decode()


def verify_password(pw, enc):
    try:
        algo,salt,digest=enc.split('$')
        if algo!='scrypt':return False
        actual=hashlib.scrypt(pw.encode(),salt=base64.b64decode(salt),n=2**14,r=8,p=1,dklen=32)
        return hmac.compare_digest(actual,base64.b64decode(digest))
    except Exception:return False

DUMMY_HASH=hash_password('timing-placeholder-not-a-user')


def require_text(val, label, min_len=1, max_len=150):
    if not isinstance(val,str) or not min_len<=len(val.strip())<=max_len:
        raise ValueError(f'{label} cần {min_len}–{max_len} ký tự.')
    return val.strip()


def number(val,label,minimum=0,maximum=1000000000):
    if isinstance(val,bool):raise ValueError(f'{label} không hợp lệ.')
    try:
        parsed=int(val)
        if str(val).strip()!=str(parsed):raise ValueError()
    except (ValueError,TypeError):raise ValueError(f'{label} phải là số nguyên.')
    if not minimum<=parsed<=maximum:raise ValueError(f'{label} vượt giới hạn cho phép.')
    return parsed


def iso_date(value):
    if not isinstance(value,str):raise ValueError('Ngày hết hạn không hợp lệ.')
    try:
        date.fromisoformat(value)
    except ValueError:raise ValueError('Ngày hết hạn phải theo định dạng YYYY-MM-DD.')
    return value


def audit(conn, pharmacy, actor, action, detail):
    conn.execute('INSERT INTO audit(pharmacy_id,actor_id,action,detail,created_at) VALUES(?,?,?,?,?)',
                 (pharmacy,actor,action,json.dumps(detail,ensure_ascii=False),now()))


def seed_demo(conn, pharmacy):
    """All demo rows are synthetic and tagged at pharmacy level."""
    samples=[
      ('Paracetamol 500mg','Paracetamol','500mg','viên','hộp','8936000000101',32000,30,0,'PAR-0427','2027-04-10',96,'Dược phẩm Minh Họa'),
      ('Vitamin C 500mg','Acid ascorbic','500mg','viên','hộp','8936000000102',56000,24,0,'VIT-1226','2026-12-18',25,'Dược phẩm Minh Họa'),
      ('Amoxicillin 500mg','Amoxicillin','500mg','viên nang','hộp','8936000000103',92000,20,1,'AMX-0527','2027-05-12',47,'Dược phẩm Minh Họa'),
      ('Natri clorid 0,9%','Natri clorid','0,9%','dung dịch','chai','8936000000104',14000,25,0,'NCL-0827','2027-08-19',14,'Dược phẩm Minh Họa'),
      ('Cetirizine 10mg','Cetirizine','10mg','viên','hộp','8936000000105',39000,22,0,'CET-1226','2026-12-08',43,'Dược phẩm Minh Họa'),
      ('Oresol','Hỗn hợp điện giải','','gói','gói','8936000000106',6500,35,0,'ORS-1027','2027-10-20',123,'Dược phẩm Minh Họa'),
    ]
    for name,active,strength,form,unit,barcode,price,reorder,rx,lot,exp,qty,supplier in samples:
        row=conn.execute('INSERT INTO products(pharmacy_id,name,active,strength,form,unit,barcode,price,reorder_point,requires_rx,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (pharmacy,name,active,strength,form,unit,barcode,price,reorder,rx,now()))
        pid=row.lastrowid
        b=conn.execute('INSERT INTO batches(pharmacy_id,product_id,lot,expires,qty,supplier,cost,status,received_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (pharmacy,pid,lot,exp,qty,supplier,price//2,'active',now()))
        conn.execute('INSERT INTO stock_moves(pharmacy_id,batch_id,change_qty,kind,reason,created_at) VALUES(?,?,?,?,?,?)',
                     (pharmacy,b.lastrowid,qty,'initial','Dữ liệu mẫu',now()))


def normalized_error(e):
    return str(e) if isinstance(e,ValueError) else 'Không thể thực hiện thao tác.'


class ApiError(Exception):
    def __init__(self,status,message):super().__init__(message);self.status=status


class Handler(BaseHTTPRequestHandler):
    server_version='PharmaVisionLocal/1.0'

    def reply(self,status,payload,extra=None):
        raw=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.headers_common('application/json; charset=utf-8',len(raw),extra)
        self.wfile.write(raw)

    def headers_common(self,ctype,length,extra=None):
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(length))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy','geolocation=(), microphone=()')
        if extra:
            for k,v in extra.items():self.send_header(k,v)
        self.end_headers()

    def cookie(self, token='', clear=False):
        s=f'{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax'
        if os.getenv('PHARMAVISION_SECURE_COOKIE')=='1':s+='; Secure'
        return s+ ('; Max-Age=0' if clear else f'; Max-Age={SESSION_AGE}')

    def origin_ok(self):
        origin=self.headers.get('Origin')
        if not origin:return True
        host=self.headers.get('Host','')
        return origin in ('http://'+host,'https://'+host)

    def json_body(self):
        try:
            count=int(self.headers.get('Content-Length','0'))
            if count<=0 or count>6*1024*1024 or self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                raise ApiError(400,'JSON không hợp lệ hoặc vượt quá 6 MB.')
            data=json.loads(self.rfile.read(count))
            if not isinstance(data,dict):raise ValueError()
            return data
        except (ValueError,TypeError,UnicodeDecodeError):raise ApiError(400,'Dữ liệu JSON không hợp lệ.')

    def me(self):
        try:
            cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
            token=cookie[COOKIE_NAME].value
        except Exception:return None
        with database() as c:
            user=c.execute('''SELECT u.id,u.pharmacy_id,u.email,u.full_name,u.role,p.name AS pharmacy_name,p.demo,s.csrf
              FROM sessions s JOIN users u ON u.id=s.user_id JOIN pharmacies p ON p.id=u.pharmacy_id
              WHERE s.token_hash=? AND s.expires_at>?''',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
            return dict(user) if user else None

    def require(self,csrf=False,admin=False):
        u=self.me()
        if not u:raise ApiError(401,'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
        if admin and u['role']!='admin':raise ApiError(403,'Chỉ quản trị viên có quyền thao tác này.')
        if csrf and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),u['csrf']):
            raise ApiError(403,'Yêu cầu thiếu mã bảo vệ CSRF.')
        return u

    def rate_limit(self,subject,limit=8,seconds=300):
        key=(self.client_address[0],subject)
        current=time.monotonic()
        with LOCK:
            attempts=[t for t in RATE.get(key,[]) if current-t<seconds]
            if len(attempts)>=limit:raise ApiError(429,'Quá nhiều yêu cầu. Vui lòng thử lại sau.')
            RATE[key]=attempts+[current]

    def issue_session(self,conn,user_id):
        token=secrets.token_urlsafe(48)
        conn.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires_at) VALUES(?,?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(),user_id,secrets.token_urlsafe(30),int(time.time())+SESSION_AGE))
        return token

    def transaction(self,conn,fn):
        with LOCK:
            conn.execute('BEGIN IMMEDIATE')
            try:
                result=fn()
                conn.execute('COMMIT')
                return result
            except Exception:
                conn.execute('ROLLBACK')
                raise

    def do_GET(self):
        try:
            path=urlsplit(self.path).path
            if path.startswith('/api/'):
                result=self.get_api(path,parse_qs(urlsplit(self.path).query))
                self.reply(200,result)
                return
            filename=ALLOWED_STATIC.get(path)
            if filename is None:raise ApiError(404,'Không tìm thấy tài nguyên.')
            data=(STATIC/filename).read_bytes()
            typ=mimetypes.guess_type(filename)[0] or 'text/plain'
            self.send_response(200)
            self.headers_common(typ+'; charset=utf-8',len(data))
            self.wfile.write(data)
        except ApiError as e:self.reply(e.status,{'error':str(e)})
        except Exception as e:
            print('GET unexpected:',repr(e))
            self.reply(500,{'error':'Lỗi máy chủ.'})

    def get_api(self,path,params):
        if path=='/api/me':
            u=self.me()
            if not u:return {'authenticated':False}
            return {'authenticated':True,'csrf':u['csrf'], 'user':{k:u[k] for k in ('id','email','full_name','role','pharmacy_name','demo')}}
        user=self.require();ph=user['pharmacy_id']
        with database() as c:
            if path=='/api/dashboard':
                products=c.execute('''SELECT p.id,p.name,p.reorder_point,COALESCE(SUM(b.qty),0) stock
                         FROM products p LEFT JOIN batches b ON b.product_id=p.id
                         WHERE p.pharmacy_id=? GROUP BY p.id''',(ph,)).fetchall()
                today=date.today().isoformat()
                low=sum(p['stock']<p['reorder_point'] for p in products)
                expiry=c.execute('SELECT COUNT(*) FROM batches WHERE pharmacy_id=? AND qty>0 AND expires<=? AND status="active"',
                                 (ph,(date.today()+timedelta(days=60)).isoformat())).fetchone()[0]
                daily=c.execute('SELECT substr(created_at,1,10) day,SUM(total) amount,COUNT(*) orders FROM sales WHERE pharmacy_id=? GROUP BY day ORDER BY day DESC LIMIT 7',(ph,)).fetchall()
                revenue=c.execute('SELECT COALESCE(SUM(total),0),COUNT(*) FROM sales WHERE pharmacy_id=? AND substr(created_at,1,10)=?',(ph,today)).fetchone()
                recent=c.execute('SELECT id,total,created_at FROM sales WHERE pharmacy_id=? ORDER BY id DESC LIMIT 6',(ph,)).fetchall()
                audit_recent=c.execute('SELECT action,detail,created_at FROM audit WHERE pharmacy_id=? ORDER BY id DESC LIMIT 6',(ph,)).fetchall()
                alerts=make_alerts(c,ph)
                return {'metrics':{'products':len(products),'stock_units':sum(p['stock'] for p in products),'low_stock':low,'expiry_risks':expiry,'revenue_today':revenue[0],'orders_today':revenue[1]},
                        'daily':[dict(x) for x in daily], 'recent_sales':[dict(x) for x in recent],
                        'recent_activity':[dict(x) for x in audit_recent], 'alerts':alerts, 'demo':bool(user['demo'])}
            if path=='/api/products':
                rows=c.execute('SELECT * FROM products WHERE pharmacy_id=? ORDER BY id DESC',(ph,)).fetchall()
                batches=c.execute('SELECT * FROM batches WHERE pharmacy_id=? ORDER BY expires, id',(ph,)).fetchall()
                grouped={}
                for b in batches:grouped.setdefault(b['product_id'],[]).append(dict(b))
                return {'products':[{**dict(p),'batches':grouped.get(p['id'],[]),'stock':sum(b['qty'] for b in grouped.get(p['id'],[])),
                                     'sellable':sum(b['qty'] for b in grouped.get(p['id'],[]) if b['expires']>=date.today().isoformat() and b['status']=='active')} for p in rows]}
            if path=='/api/customers':
                return {'customers':[dict(x) for x in c.execute('SELECT * FROM customers WHERE pharmacy_id=? ORDER BY id DESC',(ph,))]}
            customer_history=re.fullmatch(r'/api/customers/(\d+)/history',path)
            if customer_history:
                cid=int(customer_history.group(1))
                person=c.execute('SELECT id,name FROM customers WHERE id=? AND pharmacy_id=?',(cid,ph)).fetchone()
                if not person:raise ApiError(404,'Không tìm thấy khách hàng.')
                history=c.execute('''SELECT s.id,s.total,s.created_at,s.prescription_code,
                    GROUP_CONCAT(p.name || ' × ' || sl.qty, '; ') AS items
                    FROM sales s JOIN sale_lines sl ON sl.sale_id=s.id
                    JOIN products p ON p.id=sl.product_id
                    WHERE s.customer_id=? AND s.pharmacy_id=? GROUP BY s.id ORDER BY s.id DESC LIMIT 50''',(cid,ph)).fetchall()
                return {'history':[dict(x) for x in history]}
            if path=='/api/sales':
                rows=c.execute('SELECT s.*,c.name customer_name,u.full_name operator FROM sales s LEFT JOIN customers c ON s.customer_id=c.id LEFT JOIN users u ON s.verified_by=u.id WHERE s.pharmacy_id=? ORDER BY s.id DESC LIMIT 150',(ph,)).fetchall()
                lines=c.execute('''SELECT sl.*,p.name product_name,b.lot FROM sale_lines sl
                        JOIN sales s ON s.id=sl.sale_id JOIN products p ON p.id=sl.product_id JOIN batches b ON b.id=sl.batch_id
                        WHERE s.pharmacy_id=?''',(ph,)).fetchall()
                group={}
                for x in lines:group.setdefault(x['sale_id'],[]).append(dict(x))
                return {'sales':[{**dict(r),'lines':group.get(r['id'],[])} for r in rows]}
            if path=='/api/recalls':
                return {'recalls':[dict(x) for x in c.execute('''SELECT r.*,p.name product_name FROM recalls r LEFT JOIN products p ON p.id=r.product_id WHERE r.pharmacy_id=? ORDER BY r.id DESC''',(ph,))]}
            if path=='/api/forecast':
                lead=number(params.get('lead',['7'])[0],'Thời gian giao hàng',1,90)
                horizon=number(params.get('days',['14'])[0],'Khoảng dự báo',1,90)
                return forecast(c,ph,lead,horizon)
            if path=='/api/users':
                self.require(admin=True)
                return {'users':[dict(x) for x in c.execute('SELECT id,email,full_name,role,created_at FROM users WHERE pharmacy_id=? ORDER BY id',(ph,))]}
            if path=='/api/audit':
                self.require(admin=True)
                return {'audit':[dict(x) for x in c.execute('SELECT a.*,u.full_name actor FROM audit a LEFT JOIN users u ON a.actor_id=u.id WHERE a.pharmacy_id=? ORDER BY a.id DESC LIMIT 100',(ph,))]}
            if path=='/api/ai/status':
                return {'inventory_forecast':'Thống kê từ lịch sử bán; chưa dùng mô hình ML đã huấn luyện',
                        'ocr':'Tesseract cục bộ nếu máy chủ có cài đặt',
                        'barcode':'Browser BarcodeDetector (nếu được hỗ trợ) hoặc máy quét USB',
                        'drug_interactions':'Chưa kết nối kho tương tác lâm sàng đã thẩm định',
                        'drug_regulatory_api':'Chưa kết nối Hệ thống cơ sở dữ liệu về dược',
                        'zalo':'Chưa kết nối Zalo OA'}
        raise ApiError(404,'API không tồn tại.')

    def do_POST(self):
        try:
            if not self.origin_ok():raise ApiError(403,'Nguồn yêu cầu không được chấp nhận.')
            path=urlsplit(self.path).path
            if path not in {'/api/register','/api/login','/api/logout','/api/password','/api/users','/api/products','/api/stock/import','/api/stock/adjust',
                            '/api/stock/hold','/api/sales','/api/customers','/api/recalls','/api/ocr','/api/copilot'}:
                raise ApiError(404,'API không tồn tại.')
            data=self.json_body() if path!='/api/logout' else {}
            result,extra=self.post_api(path,data)
            self.reply(201 if path in ('/api/register','/api/products','/api/customers','/api/sales','/api/recalls','/api/users') else 200,result,extra)
        except ApiError as e:self.reply(e.status,{'error':str(e)})
        except (ValueError,sqlite3.IntegrityError) as e:
            self.reply(400,{'error':normalized_error(e)})
        except Exception as e:
            print('POST unexpected',repr(e))
            self.reply(500,{'error':'Lỗi máy chủ. Không có dữ liệu nào được xác nhận.'})

    def post_api(self,path,data):
        if path=='/api/register':
            self.rate_limit('registration',5,3600)
            pharmacy=require_text(data.get('pharmacy_name'),'Tên nhà thuốc',3,100)
            full_name=require_text(data.get('full_name'),'Họ tên',2,90)
            email=require_text(data.get('email'),'Email',6,250).lower()
            pw=data.get('password','')
            if not EMAIL_RE.fullmatch(email):raise ApiError(400,'Email không hợp lệ.')
            if not isinstance(pw,str) or not 10<=len(pw)<=128:raise ApiError(400,'Mật khẩu cần tối thiểu 10 ký tự.')
            if data.get('password_confirm')!=pw:raise ApiError(400,'Nhập lại mật khẩu chưa khớp.')
            if data.get('accept') is not True:raise ApiError(400,'Cần xác nhận điều khoản sử dụng bản demo.')
            demo=data.get('demo') is True
            with database() as c:
                def work():
                    if c.execute('SELECT 1 FROM users WHERE email=? COLLATE NOCASE',(email,)).fetchone():raise ApiError(409,'Email đã được sử dụng.')
                    phid=c.execute('INSERT INTO pharmacies(name,created_at,demo) VALUES(?,?,?)',(pharmacy,now(),int(demo))).lastrowid
                    uid=c.execute('INSERT INTO users(pharmacy_id,email,full_name,pass_hash,role,created_at) VALUES(?,?,?,?,?,?)',
                                 (phid,email,full_name,hash_password(pw),'admin',now())).lastrowid
                    if demo:seed_demo(c,phid)
                    audit(c,phid,uid,'account.register',{'pharmacy':pharmacy,'demo':demo})
                    return self.issue_session(c,uid)
                token=self.transaction(c,work)
            return {'ok':True}, {'Set-Cookie':self.cookie(token)}
        if path=='/api/login':
            self.rate_limit('login:'+str(data.get('email','')).lower(),10,300)
            email=str(data.get('email','')).strip().lower()
            pw=data.get('password','')
            if not isinstance(pw,str) or len(pw)>128 or len(email)>250:raise ApiError(400,'Email hoặc mật khẩu không hợp lệ.')
            with database() as c:
                row=c.execute('SELECT id,pass_hash FROM users WHERE email=? COLLATE NOCASE',(email,)).fetchone()
                if not verify_password(pw,row['pass_hash'] if row else DUMMY_HASH):raise ApiError(401,'Email hoặc mật khẩu không đúng.')
                token=self.transaction(c,lambda:self.issue_session(c,row['id']))
            return {'ok':True},{'Set-Cookie':self.cookie(token)}
        user=self.require(csrf=True)
        ph=user['pharmacy_id'];uid=user['id']
        if path=='/api/logout':
            try:
                cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
                token=cookie[COOKIE_NAME].value
                with database() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
            except Exception:pass
            return {'ok':True},{'Set-Cookie':self.cookie(clear=True)}
        if path=='/api/password':
            old=data.get('old_password');new=data.get('new_password')
            if not isinstance(old,str) or not isinstance(new,str) or not 10<=len(new)<=128:raise ApiError(400,'Mật khẩu mới cần ít nhất 10 ký tự.')
            with database() as c:
                def work():
                    current=c.execute('SELECT pass_hash FROM users WHERE id=?',(uid,)).fetchone()
                    if not verify_password(old,current['pass_hash']):raise ApiError(403,'Mật khẩu hiện tại không đúng.')
                    c.execute('UPDATE users SET pass_hash=? WHERE id=?',(hash_password(new),uid))
                    cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
                    token_hash=hashlib.sha256(cookie[COOKIE_NAME].value.encode()).hexdigest()
                    c.execute('DELETE FROM sessions WHERE user_id=? AND token_hash!=?',(uid,token_hash))
                    audit(c,ph,uid,'account.password',{})
                self.transaction(c,work)
            return {'ok':True},None
        if path=='/api/users':
            self.require(admin=True)
            email=require_text(data.get('email'),'Email',6,250).lower();name=require_text(data.get('full_name'),'Họ tên',2,90)
            pw=data.get('password','');role=data.get('role','staff')
            if not EMAIL_RE.fullmatch(email) or role not in ('admin','staff') or not isinstance(pw,str) or not 10<=len(pw)<=128:
                raise ApiError(400,'Email, vai trò hoặc mật khẩu không hợp lệ.')
            with database() as c:
                def work():
                    c.execute('INSERT INTO users(pharmacy_id,email,full_name,pass_hash,role,created_at) VALUES(?,?,?,?,?,?)',
                              (ph,email,name,hash_password(pw),role,now()))
                    audit(c,ph,uid,'account.add',{'email':email,'role':role})
                self.transaction(c,work)
            return {'ok':True},None
        if path=='/api/products':
            name=require_text(data.get('name'),'Tên thuốc',2,120)
            active=require_text(data.get('active',''),'Hoạt chất',0,160)
            strength=require_text(data.get('strength',''),'Hàm lượng',0,80)
            form=require_text(data.get('form',''),'Dạng bào chế',0,80)
            unit=require_text(data.get('unit','hộp'),'Đơn vị',1,32)
            barcode=require_text(data.get('barcode',''),'Mã vạch',0,65)
            price=number(data.get('price',0),'Giá bán',0,1000000000)
            reorder=number(data.get('reorder_point',20),'Ngưỡng tồn tối thiểu',0,10000000)
            with database() as c:
                def work():
                    pid=c.execute('INSERT INTO products(pharmacy_id,name,active,strength,form,unit,barcode,price,reorder_point,requires_rx,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (ph,name,active,strength,form,unit,barcode,price,reorder,int(data.get('requires_rx') is True),now())).lastrowid
                    audit(c,ph,uid,'product.create',{'product_id':pid,'name':name})
                    return pid
                pid=self.transaction(c,work)
            return {'ok':True,'id':pid},None
        if path=='/api/stock/import':
            pid=number(data.get('product_id'),'Sản phẩm',1)
            lot=require_text(data.get('lot'),'Số lô',1,70)
            expires=iso_date(data.get('expires'))
            qty=number(data.get('qty'),'Số lượng nhập',1,1000000)
            supplier=require_text(data.get('supplier',''),'Nhà cung cấp',0,150)
            cost=number(data.get('cost',0),'Giá nhập',0,1000000000)
            with database() as c:
                def work():
                    if not c.execute('SELECT 1 FROM products WHERE id=? AND pharmacy_id=?',(pid,ph)).fetchone():raise ApiError(404,'Sản phẩm không có trong nhà thuốc.')
                    previous=c.execute('SELECT * FROM batches WHERE pharmacy_id=? AND product_id=? AND lot=?',(ph,pid,lot)).fetchone()
                    if previous:
                        if previous['expires']!=expires:raise ApiError(409,'Lô đã có nhưng hạn sử dụng không trùng khớp. Cần kiểm duyệt.')
                        c.execute('UPDATE batches SET qty=qty+? WHERE id=?',(qty,previous['id']))
                        bid=previous['id']
                    else:
                        blocked=c.execute('SELECT 1 FROM recalls WHERE pharmacy_id=? AND lot=? AND (product_id IS NULL OR product_id=?)',(ph,lot,pid)).fetchone()
                        bid=c.execute('INSERT INTO batches(pharmacy_id,product_id,lot,expires,qty,supplier,cost,status,received_at) VALUES(?,?,?,?,?,?,?,?,?)',
                            (ph,pid,lot,expires,qty,supplier,cost,'quarantine' if blocked else 'active',now())).lastrowid
                    c.execute('INSERT INTO stock_moves(pharmacy_id,batch_id,change_qty,kind,reason,actor_id,created_at) VALUES(?,?,?,?,?,?,?)',
                              (ph,bid,qty,'import','Nhập từ nhà cung cấp: '+supplier,uid,now()))
                    audit(c,ph,uid,'stock.import',{'product_id':pid,'batch_id':bid,'qty':qty,'lot':lot})
                    return bid
                bid=self.transaction(c,work)
            return {'ok':True,'batch_id':bid},None
        if path=='/api/stock/adjust':
            self.require(admin=True)
            bid=number(data.get('batch_id'),'Lô',1)
            delta=number(data.get('delta'),'Chênh lệch',-1000000,1000000)
            reason=require_text(data.get('reason'),'Lý do kiểm kê',5,200)
            if delta==0:raise ApiError(400,'Số lượng điều chỉnh phải khác 0.')
            with database() as c:
                def work():
                    b=c.execute('SELECT qty FROM batches WHERE id=? AND pharmacy_id=?',(bid,ph)).fetchone()
                    if not b:raise ApiError(404,'Không tìm thấy lô thuốc.')
                    if b['qty']+delta<0:raise ApiError(409,'Điều chỉnh vượt quá số lượng tồn.')
                    c.execute('UPDATE batches SET qty=qty+? WHERE id=?',(delta,bid))
                    c.execute('INSERT INTO stock_moves(pharmacy_id,batch_id,change_qty,kind,reason,actor_id,created_at) VALUES(?,?,?,?,?,?,?)',
                             (ph,bid,delta,'adjust',reason,uid,now()))
                    audit(c,ph,uid,'stock.adjust',{'batch_id':bid,'delta':delta,'reason':reason})
                self.transaction(c,work)
            return {'ok':True},None
        if path=='/api/stock/hold':
            self.require(admin=True)
            bid=number(data.get('batch_id'),'Lô',1)
            hold=data.get('hold') is True
            reason=require_text(data.get('reason'),'Lý do',4,200)
            with database() as c:
                def work():
                    row=c.execute('SELECT b.*,p.name FROM batches b JOIN products p ON b.product_id=p.id WHERE b.id=? AND b.pharmacy_id=?',(bid,ph)).fetchone()
                    if not row:raise ApiError(404,'Không tìm thấy lô thuốc.')
                    if not hold and c.execute('SELECT 1 FROM recalls WHERE pharmacy_id=? AND lot=? AND (product_id IS NULL OR product_id=?)',(ph,row['lot'],row['product_id'])).fetchone():
                        raise ApiError(409,'Lô đã được đánh dấu theo thông báo thu hồi. Không thể bỏ khóa khi cảnh báo còn hiệu lực.')
                    c.execute('UPDATE batches SET status=? WHERE id=?',('quarantine' if hold else 'active',bid))
                    audit(c,ph,uid,'stock.hold' if hold else 'stock.release',{'batch_id':bid,'reason':reason})
                self.transaction(c,work)
            return {'ok':True},None
        if path=='/api/sales':
            items=data.get('items')
            if not isinstance(items,list) or not 1<=len(items)<=50:raise ApiError(400,'Đơn bán cần 1–50 sản phẩm.')
            if data.get('pharmacist_verified') is not True:raise ApiError(400,'Dược sĩ cần xác nhận đã kiểm tra đơn hàng.')
            customer_id=data.get('customer_id')
            cid=number(customer_id,'Khách hàng',1) if customer_id not in (None,'') else None
            code=require_text(data.get('prescription_code',''),'Mã đơn điện tử',0,100)
            consolidated={}
            for item in items:
                if not isinstance(item,dict):raise ApiError(400,'Sản phẩm trong giỏ hàng không hợp lệ.')
                pid=number(item.get('product_id'),'Sản phẩm',1)
                qty=number(item.get('qty'),'Số lượng bán',1,100000)
                consolidated[pid]=consolidated.get(pid,0)+qty
            with database() as c:
                def work():
                    if cid and not c.execute('SELECT 1 FROM customers WHERE id=? AND pharmacy_id=?',(cid,ph)).fetchone():
                        raise ApiError(404,'Không tìm thấy khách hàng.')
                    plans=[];total=0
                    for pid,qty in consolidated.items():
                        p=c.execute('SELECT * FROM products WHERE id=? AND pharmacy_id=?',(pid,ph)).fetchone()
                        if not p:raise ApiError(404,'Sản phẩm không thuộc nhà thuốc.')
                        if p['requires_rx'] and (data.get('rx_verified') is not True or not code):
                            raise ApiError(400,f'{p["name"]} là thuốc kê đơn. Cần xác minh đơn và nhập mã đơn hợp lệ (chưa tự kiểm tra với Bộ Y tế).')
                        eligible=c.execute('SELECT * FROM batches WHERE product_id=? AND pharmacy_id=? AND status="active" AND expires>=? AND qty>0 ORDER BY expires,id',(pid,ph,date.today().isoformat())).fetchall()
                        rem=qty
                        for b in eligible:
                            take=min(b['qty'],rem)
                            if take:plans.append((pid,b['id'],take,p['price']));rem-=take
                            if rem==0:break
                        if rem:raise ApiError(409,f'{p["name"]} chỉ còn {qty-rem} đơn vị đủ điều kiện bán.')
                        total+=qty*p['price']
                    sid=c.execute('INSERT INTO sales(pharmacy_id,customer_id,total,created_at,verified_by,prescription_code) VALUES(?,?,?,?,?,?)',
                                  (ph,cid,total,now(),uid,code)).lastrowid
                    for pid,bid,qty,price in plans:
                        c.execute('UPDATE batches SET qty=qty-? WHERE id=?',(qty,bid))
                        c.execute('INSERT INTO sale_lines(sale_id,product_id,batch_id,qty,unit_price) VALUES(?,?,?,?,?)',(sid,pid,bid,qty,price))
                        c.execute('INSERT INTO stock_moves(pharmacy_id,batch_id,change_qty,kind,reason,actor_id,created_at) VALUES(?,?,?,?,?,?,?)',
                                  (ph,bid,-qty,'sale',f'Đơn bán #{sid}',uid,now()))
                    audit(c,ph,uid,'sale.create',{'sale_id':sid,'total':total,'items':consolidated})
                    return sid,total
                sid,total=self.transaction(c,work)
            return {'ok':True,'id':sid,'total':total},None
        if path=='/api/customers':
            name=require_text(data.get('name'),'Tên khách hàng',2,100)
            phone=require_text(data.get('phone',''),'Số điện thoại',0,30)
            consent=data.get('consent') is True
            allergies=require_text(data.get('allergies',''),'Dị ứng',0,500)
            meds=require_text(data.get('reported_meds',''),'Thuốc khai báo',0,500)
            notes=require_text(data.get('care_notes',''),'Ghi chú',0,600)
            if (allergies or meds or notes) and not consent:
                raise ApiError(400,'Cần có sự đồng ý của khách hàng trước khi lưu thông tin sức khỏe.')
            with database() as c:
                def work():
                    cid=c.execute('INSERT INTO customers(pharmacy_id,name,phone,consent,consent_at,allergies,reported_meds,care_notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                                (ph,name,phone,int(consent),now() if consent else None,allergies,meds,notes,now())).lastrowid
                    audit(c,ph,uid,'customer.create',{'customer_id':cid,'consent':consent})
                    return cid
                cid=self.transaction(c,work)
            return {'ok':True,'id':cid},None
        if path=='/api/recalls':
            self.require(admin=True)
            lot=require_text(data.get('lot'),'Số lô',1,70)
            reason=require_text(data.get('reason'),'Lý do',5,500)
            source=require_text(data.get('source','Nhập thủ công'),'Nguồn',3,200)
            pid=data.get('product_id')
            pid=number(pid,'Sản phẩm',1) if pid not in (None,'') else None
            with database() as c:
                def work():
                    if pid and not c.execute('SELECT 1 FROM products WHERE id=? AND pharmacy_id=?',(pid,ph)).fetchone():
                        raise ApiError(404,'Sản phẩm không thuộc nhà thuốc.')
                    rid=c.execute('INSERT INTO recalls(pharmacy_id,product_id,lot,reason,source,created_at) VALUES(?,?,?,?,?,?)',
                                (ph,pid,lot,reason,source,now())).lastrowid
                    cursor=c.execute('UPDATE batches SET status="quarantine" WHERE pharmacy_id=? AND lot=?'+(' AND product_id=?' if pid else ''),
                                     (ph,lot,pid) if pid else (ph,lot))
                    audit(c,ph,uid,'recall.manual',{'recall_id':rid,'lot':lot,'matched':cursor.rowcount})
                    return rid,cursor.rowcount
                rid,matched=self.transaction(c,work)
            return {'ok':True,'id':rid,'matched':matched},None
        if path=='/api/copilot':
            question=require_text(data.get('question'),'Nội dung tra cứu',2,300)
            with database() as c:
                rows=c.execute('SELECT * FROM products WHERE pharmacy_id=?',(ph,)).fetchall()
                matches=[r for r in rows if question.casefold() in r['name'].casefold() or question.casefold() in r['active'].casefold()]
                if not matches:
                    tokens=[s for s in re.split(r'\W+',question.casefold()) if len(s)>=4]
                    matches=[r for r in rows if any(t in (r['name']+' '+r['active']).casefold() for t in tokens)]
                responses=[]
                for r in matches[:4]:
                    b=c.execute('SELECT lot,expires,qty,status FROM batches WHERE product_id=? AND pharmacy_id=?',(r['id'],ph)).fetchall()
                    responses.append({'name':r['name'],'active':r['active'],'strength':r['strength'],'form':r['form'],
                                      'requires_rx':bool(r['requires_rx']), 'lots':[dict(x) for x in b],
                                      'sellable':sum(x['qty'] for x in b if x['expires']>=date.today().isoformat() and x['status']=='active')})
            return {'matches':responses,'message':'Tra cứu danh mục và tồn kho nội bộ; chưa xác minh thông tin lâm sàng hoặc tương tác thuốc. Dược sĩ phải kiểm tra nguồn chuyên môn đáng tin cậy và đơn thuốc.'},None
        if path=='/api/ocr':
            src=data.get('image_data','')
            if not isinstance(src,str) or not re.match(r'^data:image/(png|jpeg|webp);base64,',src,re.I):
                raise ApiError(400,'Chỉ nhận ảnh PNG, JPEG hoặc WEBP.')
            if not shutil.which('tesseract'):raise ApiError(501,'Máy chủ chưa cài Tesseract OCR. Có thể nhập lô thủ công hoặc cài Tesseract và dữ liệu ngôn ngữ Việt.')
            try: raw=base64.b64decode(src.split(',',1)[1],validate=True)
            except Exception:raise ApiError(400,'Ảnh không hợp lệ.')
            if len(raw)>3*1024*1024:raise ApiError(400,'Ảnh vượt quá 3 MB.')
            # Validate image signatures (do not trust MIME alone).
            if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff') or (raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')):
                raise ApiError(400,'Tệp không đúng định dạng ảnh.')
            with tempfile.NamedTemporaryFile(suffix='.img') as temp:
                temp.write(raw);temp.flush()
                langs=subprocess.run(['tesseract','--list-langs'],capture_output=True,text=True,timeout=6).stdout
                lang='vie+eng' if 'vie' in langs and 'eng' in langs else ('vie' if 'vie' in langs else 'eng')
                try:proc=subprocess.run(['tesseract',temp.name,'stdout','-l',lang],capture_output=True,text=True,timeout=18)
                except subprocess.TimeoutExpired:raise ApiError(408,'OCR mất quá nhiều thời gian; vui lòng thử ảnh rõ hơn.')
            if proc.returncode!=0:raise ApiError(422,'OCR không nhận diện được ảnh này.')
            txt=proc.stdout[:6000]
            lots=re.findall(r'(?:lô|lot|batch)\s*[:#\-]?\s*([A-Z0-9\-]{4,25})',txt,re.I)
            dates=re.findall(r'\b(?:0?[1-9]|[12]\d|3[01])[/\-](?:0?[1-9]|1[012])[/\-]20\d{2}\b|\b20\d{2}-\d{2}-\d{2}\b',txt)
            return {'text':txt,'lot_candidates':lots[:5],'date_candidates':dates[:6],
                    'notice':'OCR chỉ là bản nháp. Dược sĩ phải soát lại tên thuốc, số lượng, số lô, hạn dùng trước khi nhập kho.'},None
        raise ApiError(404,'API không tồn tại.')

    def do_DELETE(self):
        try:
            if not self.origin_ok():raise ApiError(403,'Nguồn yêu cầu không hợp lệ.')
            user=self.require(csrf=True,admin=True)
            path=urlsplit(self.path).path
            match=re.fullmatch(r'/api/customers/(\d+)',path)
            if not match:raise ApiError(404,'Đường dẫn API không tồn tại.')
            cid=int(match.group(1));ph=user['pharmacy_id']
            with database() as c:
                def work():
                    cur=c.execute('DELETE FROM customers WHERE id=? AND pharmacy_id=?',(cid,ph))
                    if not cur.rowcount:raise ApiError(404,'Không tìm thấy khách hàng.')
                    audit(c,ph,user['id'],'customer.delete',{'customer_id':cid})
                self.transaction(c,work)
            self.reply(200,{'ok':True})
        except ApiError as e:self.reply(e.status,{'error':str(e)})
        except Exception:self.reply(500,{'error':'Lỗi máy chủ.'})


def make_alerts(c,ph):
    today=date.today();limit=(today+timedelta(days=60)).isoformat()
    result=[]
    rows=c.execute('''SELECT p.id,p.name,p.reorder_point,COALESCE(SUM(b.qty),0) qty
          FROM products p LEFT JOIN batches b ON b.product_id=p.id
          WHERE p.pharmacy_id=? GROUP BY p.id HAVING qty<p.reorder_point ORDER BY qty''',(ph,)).fetchall()
    for x in rows:result.append({'type':'low','severity':'warning','title':'Tồn kho thấp · '+x['name'],'detail':f'{x["qty"]} đơn vị / ngưỡng {x["reorder_point"]}'})
    b=c.execute('''SELECT b.*,p.name FROM batches b JOIN products p ON p.id=b.product_id
             WHERE b.pharmacy_id=? AND b.qty>0 AND b.expires<=? ORDER BY b.expires LIMIT 30''',(ph,limit)).fetchall()
    for x in b:
        expired=x['expires']<today.isoformat()
        result.append({'type':'expiry','severity':'danger' if expired else 'warning',
                       'title':('Đã hết hạn' if expired else 'Sắp hết hạn')+' · '+x['name'],
                       'detail':f'Lô {x["lot"]} · HSD {x["expires"]} · {x["qty"]} đơn vị'})
    held=c.execute('SELECT b.lot,p.name,b.qty FROM batches b JOIN products p ON b.product_id=p.id WHERE b.pharmacy_id=? AND b.status="quarantine" AND b.qty>0 LIMIT 20',(ph,)).fetchall()
    for x in held:result.append({'type':'hold','severity':'danger','title':'Lô đang cách ly · '+x['name'],'detail':f'Lô {x["lot"]} · {x["qty"]} đơn vị không được bán'})
    return result


def forecast(c,ph,lead,horizon):
    products=c.execute('''SELECT p.id,p.name,p.reorder_point,COALESCE(SUM(b.qty),0) stock
        FROM products p LEFT JOIN batches b ON p.id=b.product_id WHERE p.pharmacy_id=? GROUP BY p.id ORDER BY p.name''',(ph,)).fetchall()
    rows=[]
    for p in products:
        sales=c.execute('''SELECT substr(s.created_at,1,10) day,SUM(sl.qty) qty FROM sale_lines sl JOIN sales s ON sl.sale_id=s.id
            WHERE s.pharmacy_id=? AND sl.product_id=? AND s.created_at>=? GROUP BY day''',
            (ph,p['id'],(date.today()-timedelta(days=29)).isoformat())).fetchall()
        total=sum(x['qty'] for x in sales)
        # 30-day average is intentionally a transparent baseline, not a trained AI model.
        avg=total/30
        demand=round(avg*horizon,1)
        target=round(avg*(lead+horizon)*1.2)
        suggested=max(0,target-p['stock'])
        rows.append({'product_id':p['id'],'name':p['name'],'stock':p['stock'],'sold_30d':total,
                     'avg_daily':round(avg,2),'demand':demand,'suggested':suggested,
                     'confidence':'Dữ liệu hạn chế' if total<8 else 'Tham khảo',
                     'method':'Bình quân 30 ngày + tồn kho an toàn 20%'})
    return {'rows':rows,'lead':lead,'days':horizon,'disclaimer':'Ước tính thống kê từ doanh số thực trong hệ thống. Chưa tính mùa vụ, dịch tễ, xu hướng bên ngoài hoặc mô hình AI đã huấn luyện. Cần được người phụ trách duyệt.'}


def main():
    parser=argparse.ArgumentParser(description='PharmaVision AI — local demo')
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--reset-email',help='Đặt lại mật khẩu qua quyền truy cập máy chủ')
    args=parser.parse_args()
    init_database()
    if args.reset_email:
        from getpass import getpass
        p1=getpass('Mật khẩu mới (10–128 ký tự): ')
        p2=getpass('Nhập lại mật khẩu: ')
        if p1!=p2 or not 10<=len(p1)<=128:parser.error('Mật khẩu không hợp lệ hoặc không trùng khớp.')
        with database() as c:
            c.execute('BEGIN IMMEDIATE')
            user=c.execute('SELECT id FROM users WHERE email=? COLLATE NOCASE',(args.reset_email,)).fetchone()
            if not user:parser.error('Không tìm thấy tài khoản email này.')
            c.execute('UPDATE users SET pass_hash=? WHERE id=?',(hash_password(p1),user['id']))
            c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
            c.execute('COMMIT')
        print('Đã đặt lại mật khẩu và đăng xuất các phiên cũ.')
        return
    if args.host not in ('127.0.0.1','localhost','::1'):
        print('WARNING: demo server is NOT hardened for public Internet. Use localhost only.')
    srv=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'PharmaVision AI: http://{args.host}:{args.port}')
    try:srv.serve_forever()
    except KeyboardInterrupt:print('\nServer stopped.')
    finally:srv.server_close()


if __name__=='__main__':main()
