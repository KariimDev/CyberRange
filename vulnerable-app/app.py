import os, json, uuid, mimetypes
from io import BytesIO
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import requests as http_requests
from flask import (Flask, request, render_template_string, jsonify,
                   session, redirect, url_for, flash, send_file)

app = Flask(__name__)
app.secret_key = "nscs_gate_secure_session_key"  # Vulnerability: weak static key

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL", "http://localstack:4566")
AWS_REGION     = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
BUCKET         = "sensitive-data-bucket"

def get_client(service):
    return boto3.client(service, endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION,
                        config=Config(connect_timeout=3, read_timeout=3,
                                      retries={'max_attempts': 1}))

def load_cloud_config():
    try:
        ssm = get_client('ssm')
        p = ssm.get_parameter(Name='/prod/app/config', WithDecryption=True)
        return json.loads(p['Parameter']['Value'])
    except Exception as e:
        return {"error": str(e)}

def fmt_size(n):
    for u in ['B','KB','MB','GB']:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

def file_icon(key):
    ext = key.rsplit('.',1)[-1].lower() if '.' in key else ''
    m = {'pdf':'fa-file-pdf','doc':'fa-file-word','docx':'fa-file-word',
         'xls':'fa-file-excel','xlsx':'fa-file-excel','zip':'fa-file-zipper',
         'tar':'fa-file-zipper','gz':'fa-file-zipper','png':'fa-file-image',
         'jpg':'fa-file-image','jpeg':'fa-file-image','gif':'fa-file-image',
         'svg':'fa-file-image','mp4':'fa-file-video','mov':'fa-file-video',
         'mp3':'fa-file-audio','wav':'fa-file-audio','py':'fa-file-code',
         'js':'fa-file-code','html':'fa-file-code','css':'fa-file-code',
         'json':'fa-file-code','sh':'fa-file-code','env':'fa-file-shield',
         'pem':'fa-file-shield','key':'fa-file-shield','csv':'fa-file-csv',
         'sql':'fa-database','txt':'fa-file-lines','md':'fa-file-lines','log':'fa-file-lines'}
    return m.get(ext, 'fa-file')

CLOUD_CONFIG = load_cloud_config()

# ─────────────────────────────────────────────────────────────────────────────
# BASE TEMPLATE  (sidebar layout)
# ─────────────────────────────────────────────────────────────────────────────
BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NSCS-Gate — {{ page_title }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#080c18;--sidebar:#0c1220;--card:rgba(255,255,255,.04);
  --border:rgba(255,255,255,.08);--primary:#4f8ef7;--primary-d:#3474d4;
  --secondary:#a78bfa;--success:#34d399;--danger:#f87171;--warn:#fbbf24;
  --text:#e2e8f0;--muted:#64748b;--dim:#94a3b8;--sw:248px;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex}

/* ── Sidebar ── */
.sidebar{width:var(--sw);min-height:100vh;background:var(--sidebar);
  border-right:1px solid var(--border);display:flex;flex-direction:column;
  position:fixed;top:0;left:0;z-index:100}
.sb-brand{padding:24px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px}
.sb-brand .icon{width:38px;height:38px;border-radius:10px;
  background:linear-gradient(135deg,var(--primary),var(--secondary));
  display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.sb-brand .name{font-size:15px;font-weight:700;color:var(--text)}
.sb-brand .tag{font-size:11px;color:var(--muted);margin-top:1px}
.sb-user{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px}
.avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}
.sb-user .uname{font-size:13px;font-weight:600}
.sb-user .urole{font-size:11px;color:var(--muted)}
nav{flex:1;padding:12px 10px}
.nav-item{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;
  color:var(--dim);text-decoration:none;font-size:13.5px;font-weight:500;
  transition:all .2s;margin-bottom:2px}
.nav-item:hover{background:rgba(255,255,255,.06);color:var(--text)}
.nav-item.active{background:rgba(79,142,247,.15);color:var(--primary);border:1px solid rgba(79,142,247,.25)}
.nav-item i{width:18px;text-align:center;font-size:14px}
.nav-section{padding:10px 12px 4px;font-size:10px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em}
.sb-footer{padding:16px 10px;border-top:1px solid var(--border)}
.logout-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;
  color:var(--dim);text-decoration:none;font-size:13px;transition:all .2s}
.logout-btn:hover{background:rgba(248,113,113,.1);color:var(--danger)}

/* ── Main ── */
.main{margin-left:var(--sw);flex:1;display:flex;flex-direction:column;min-height:100vh}
.topbar{padding:16px 32px;border-bottom:1px solid var(--border);
  background:rgba(8,12,24,.8);backdrop-filter:blur(10px);
  display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}
.topbar h1{font-size:20px;font-weight:700}
.topbar .breadcrumb{font-size:12px;color:var(--muted);margin-top:2px}
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;
  font-size:11px;font-weight:600}
.badge-primary{background:rgba(79,142,247,.15);color:var(--primary);border:1px solid rgba(79,142,247,.25)}
.badge-success{background:rgba(52,211,153,.12);color:var(--success);border:1px solid rgba(52,211,153,.2)}
.badge-danger{background:rgba(248,113,113,.12);color:var(--danger);border:1px solid rgba(248,113,113,.2)}
.badge-warn{background:rgba(251,191,36,.12);color:var(--warn);border:1px solid rgba(251,191,36,.2)}
.content{padding:28px 32px;flex:1}

/* ── Cards ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:24px;margin-bottom:20px}
.card-title{font-size:15px;font-weight:600;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.card-sub{font-size:13px;color:var(--muted);margin-bottom:20px}

/* ── Stats ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:20px;text-align:center}
.stat-card .stat-icon{font-size:24px;margin-bottom:10px}
.stat-card .stat-val{font-size:28px;font-weight:700;line-height:1}
.stat-card .stat-label{font-size:12px;color:var(--muted);margin-top:6px}

/* ── Forms ── */
.form-group{margin-bottom:16px}
label{display:block;font-size:13px;font-weight:500;color:var(--dim);margin-bottom:6px}
input[type=text],input[type=password],input[type=email],textarea,select{
  width:100%;padding:10px 14px;background:rgba(255,255,255,.05);
  border:1px solid var(--border);border-radius:8px;color:var(--text);
  font-family:'Inter',sans-serif;font-size:14px;transition:border .2s;outline:none}
input:focus,textarea:focus,select:focus{border-color:var(--primary)}
textarea{resize:vertical;min-height:90px}
.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 18px;
  border:none;border-radius:8px;font-size:13.5px;font-weight:600;
  cursor:pointer;text-decoration:none;transition:all .2s}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{background:var(--primary-d);transform:translateY(-1px)}
.btn-success{background:rgba(52,211,153,.15);color:var(--success);border:1px solid rgba(52,211,153,.3)}
.btn-success:hover{background:rgba(52,211,153,.25)}
.btn-danger{background:rgba(248,113,113,.12);color:var(--danger);border:1px solid rgba(248,113,113,.25)}
.btn-danger:hover{background:rgba(248,113,113,.22)}
.btn-ghost{background:rgba(255,255,255,.06);color:var(--dim);border:1px solid var(--border)}
.btn-ghost:hover{background:rgba(255,255,255,.1);color:var(--text)}
.btn-sm{padding:6px 12px;font-size:12px}

/* ── Alerts ── */
.alert{padding:12px 16px;border-radius:8px;margin-bottom:16px;font-size:13.5px;
  display:flex;align-items:flex-start;gap:10px}
.alert-error{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.25);color:#fca5a5}
.alert-success{background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.2);color:#6ee7b7}

/* ── Table ── */
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;padding:10px 14px;
  border-bottom:1px solid var(--border)}
td{padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.04);
  font-size:13.5px;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02)}

/* ── File upload drop zone ── */
.drop-zone{border:2px dashed var(--border);border-radius:12px;padding:36px 20px;
  text-align:center;cursor:pointer;transition:all .2s;position:relative}
.drop-zone:hover,.drop-zone.drag-over{border-color:var(--primary);background:rgba(79,142,247,.06)}
.drop-zone input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
.drop-zone .dz-icon{font-size:32px;color:var(--muted);margin-bottom:10px}
.drop-zone .dz-text{font-size:14px;font-weight:500;color:var(--dim)}
.drop-zone .dz-hint{font-size:12px;color:var(--muted);margin-top:4px}

/* ── Code / terminal output ── */
.terminal{background:#020408;border:1px solid rgba(79,142,247,.2);border-radius:10px;
  padding:18px;font-family:'JetBrains Mono',monospace;font-size:13px;
  color:#a7f3d0;white-space:pre-wrap;word-break:break-all;max-height:400px;overflow-y:auto}
.terminal-bar{background:rgba(79,142,247,.08);border:1px solid rgba(79,142,247,.2);
  border-bottom:none;border-radius:10px 10px 0 0;padding:10px 16px;
  display:flex;align-items:center;gap:6px}
.dot{width:10px;height:10px;border-radius:50%}

/* ── Config dump ── */
.config-block{background:#020408;border:1px solid var(--border);border-radius:10px;
  padding:18px;font-family:monospace;font-size:12.5px;color:#86efac;
  white-space:pre-wrap;max-height:300px;overflow-y:auto}

/* ── 2-col grid ── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:800px){.grid-2{grid-template-columns:1fr}}

/* ── Auth pages ── */
.auth-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(ellipse at 30% 50%,rgba(79,142,247,.08) 0%,transparent 60%),var(--bg)}
.auth-card{width:100%;max-width:400px;background:rgba(255,255,255,.04);
  border:1px solid var(--border);border-radius:16px;padding:36px}
.auth-logo{text-align:center;margin-bottom:28px}
.auth-logo .icon{width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,var(--primary),var(--secondary));
  display:inline-flex;align-items:center;justify-content:center;font-size:24px;margin-bottom:12px}
.auth-logo h2{font-size:22px;font-weight:700}
.auth-logo p{font-size:13px;color:var(--muted);margin-top:4px}
.auth-footer{text-align:center;margin-top:20px;font-size:13px;color:var(--muted)}
.auth-footer a{color:var(--primary);text-decoration:none}
</style>
</head>
<body>
{% if session.get('logged_in') %}
<aside class="sidebar">
  <div class="sb-brand">
    <div class="icon">⚡</div>
    <div><div class="name">NSCS-Gate</div><div class="tag">Cloud Platform</div></div>
  </div>
  <div class="sb-user">
    <div class="avatar">{{ session.get('username','?')[0]|upper }}</div>
    <div>
      <div class="uname">{{ session.get('username') }}</div>
      <div class="urole">Cloud User</div>
    </div>
  </div>
  <nav>
    <div class="nav-section">Main</div>
    <a href="/dashboard" class="nav-item {{ 'active' if active=='dashboard' else '' }}">
      <i class="fas fa-home"></i> Dashboard
    </a>
    <a href="/drive" class="nav-item {{ 'active' if active=='drive' else '' }}">
      <i class="fas fa-cloud-arrow-up"></i> Cloud Drive
    </a>
    <div class="nav-section" style="margin-top:8px">Cloud Services</div>
    <a href="/processing" class="nav-item {{ 'active' if active=='processing' else '' }}">
      <i class="fas fa-bolt"></i> Async Processing
    </a>
    <a href="/serverless" class="nav-item {{ 'active' if active=='serverless' else '' }}">
      <i class="fas fa-code"></i> Serverless APIs
    </a>
    <a href="/webhooks" class="nav-item {{ 'active' if active=='webhooks' else '' }}">
      <i class="fas fa-link"></i> Webhooks
    </a>
  </nav>
  <div class="sb-footer">
    <a href="/logout" class="logout-btn"><i class="fas fa-right-from-bracket"></i> Sign Out</a>
  </div>
</aside>
<div class="main">
  <div class="topbar">
    <div>
      <h1>{{ page_title }}</h1>
      <div class="breadcrumb">NSCS-Gate / {{ page_title }}</div>
    </div>
    <span class="badge badge-success"><i class="fas fa-circle" style="font-size:8px"></i> Cloud Connected</span>
  </div>
  <div class="content">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
        <div class="alert {{ 'alert-success' if cat=='success' else 'alert-error' }}">
          <i class="fas {{ 'fa-check-circle' if cat=='success' else 'fa-triangle-exclamation' }}"></i> {{ msg }}
        </div>
      {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
</div>
{% else %}
  {% block auth %}{% endblock %}
{% endif %}
<script>
// Drag-and-drop for upload zones
document.querySelectorAll('.drop-zone').forEach(zone => {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drag-over');
    const fi = zone.querySelector('input[type=file]'); if(fi) fi.files = e.dataTransfer.files;
    zone.querySelector('.dz-text').textContent = `${e.dataTransfer.files.length} file(s) selected`; });
  const fi = zone.querySelector('input[type=file]');
  if(fi) fi.addEventListener('change', () => {
    zone.querySelector('.dz-text').textContent = fi.files.length ? `${fi.files.length} file(s) selected — ready to upload` : 'Click or drag a file here'; });
});
</script>
</body></html>"""

def render(template_content, **kwargs):
    full = BASE.replace("{% block content %}{% endblock %}", template_content)\
               .replace("{% block auth %}{% endblock %}", "")
    return render_template_string(full, **kwargs)

def render_auth(auth_content, **kwargs):
    full = BASE.replace("{% block content %}{% endblock %}", "")\
               .replace("{% block auth %}{% endblock %}", auth_content)
    return render_template_string(full, **kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# AUTH  (Login / Register / Logout)
# ─────────────────────────────────────────────────────────────────────────────
LOGIN_CONTENT = """
<div class="auth-wrap">
<div class="auth-card">
  <div class="auth-logo">
    <div class="icon">⚡</div>
    <h2>NSCS-Gate</h2>
    <p>Sign in to your cloud account</p>
  </div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert {{ 'alert-success' if cat=='success' else 'alert-error' }}">
        <i class="fas {{ 'fa-check-circle' if cat=='success' else 'fa-triangle-exclamation' }}"></i> {{ msg }}
      </div>
    {% endfor %}
  {% endwith %}
  <form action="/login" method="POST">
    <div class="form-group"><label>Username</label><input type="text" name="username" required autofocus></div>
    <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
    <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:6px">
      <i class="fas fa-right-to-bracket"></i> Sign In
    </button>
  </form>
  <div class="auth-footer">No account? <a href="/register">Create one</a></div>
</div></div>"""

REGISTER_CONTENT = """
<div class="auth-wrap">
<div class="auth-card">
  <div class="auth-logo">
    <div class="icon">⚡</div>
    <h2>Create Account</h2>
    <p>Join the NSCS-Gate cloud platform</p>
  </div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert {{ 'alert-success' if cat=='success' else 'alert-error' }}">
        <i class="fas {{ 'fa-check-circle' if cat=='success' else 'fa-triangle-exclamation' }}"></i> {{ msg }}
      </div>
    {% endfor %}
  {% endwith %}
  <form action="/register" method="POST">
    <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
    <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
    <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
    <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:6px">
      <i class="fas fa-user-plus"></i> Create Account
    </button>
  </form>
  <div class="auth-footer">Already have an account? <a href="/">Sign in</a></div>
</div></div>"""

@app.route("/")
def index():
    if session.get('logged_in'): return redirect(url_for('dashboard'))
    return render_auth(LOGIN_CONTENT)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "GET":
        return render_auth(REGISTER_CONTENT)
    username = request.form.get("username")
    email    = request.form.get("email")
    password = request.form.get("password")  # Vulnerability: stored plaintext
    user_id  = "USR" + uuid.uuid4().hex[:6].upper()
    try:
        get_client('dynamodb').put_item(TableName="users", Item={
            'user_id':  {'S': user_id}, 'username': {'S': username},
            'email':    {'S': email},   'password': {'S': password},
            'role':     {'S': 'user'}
        })
        flash("Account created! You can now log in.", "success")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('register'))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username","")
    password = request.form.get("password","")
    try:
        # Vulnerability: full table scan allows user enumeration
        resp = get_client('dynamodb').scan(TableName="users")
        record = next((i for i in resp.get('Items',[])
                       if i.get('username',{}).get('S') == username), None)
        if record and record.get('password',{}).get('S') == password:
            session.update({'logged_in': True, 'username': username,
                            'user_id': record.get('user_id',{}).get('S',''),
                            'role': record.get('role',{}).get('S','user')})
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid username or password.")
    except Exception as e:
        flash(f"Login error: {str(e)}")
    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
DASHBOARD_CONTENT = """
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-icon" style="color:#4f8ef7"><i class="fas fa-bucket"></i></div>
    <div class="stat-val" style="color:#4f8ef7">{{ stats.buckets }}</div>
    <div class="stat-label">S3 Buckets</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="color:#a78bfa"><i class="fas fa-database"></i></div>
    <div class="stat-val" style="color:#a78bfa">{{ stats.users }}</div>
    <div class="stat-label">DynamoDB Users</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="color:#34d399"><i class="fas fa-file"></i></div>
    <div class="stat-val" style="color:#34d399">{{ stats.my_files }}</div>
    <div class="stat-label">My Files (S3)</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="color:#fbbf24"><i class="fas fa-envelope"></i></div>
    <div class="stat-val" style="color:#fbbf24">{{ stats.queue_msgs }}</div>
    <div class="stat-label">SQS Queue Depth</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title"><i class="fas fa-sliders" style="color:var(--primary)"></i> SSM App Configuration</div>
    <div class="card-sub">Live config loaded from AWS Systems Manager Parameter Store</div>
    <!-- Vulnerability: dumps SSM secrets directly to the dashboard -->
    <div class="config-block">{{ config | tojson(indent=2) }}</div>
  </div>
  <div class="card">
    <div class="card-title"><i class="fas fa-circle-info" style="color:var(--secondary)"></i> Cloud Account Info</div>
    <div class="card-sub">Active session details from STS</div>
    <table>
      <tr><td style="color:var(--muted);width:120px">Account ID</td><td>000000000000</td></tr>
      <tr><td style="color:var(--muted)">Region</td><td>{{ region }}</td></tr>
      <tr><td style="color:var(--muted)">Username</td><td>{{ session.get('username') }}</td></tr>
      <tr><td style="color:var(--muted)">Role</td><td>
        <span class="badge {{ 'badge-danger' if session.get('role')=='administrator' else 'badge-primary' }}">
          {{ session.get('role','user') }}
        </span></td></tr>
      <tr><td style="color:var(--muted)">LocalStack</td><td><a href="{{ localstack_url }}" style="color:var(--primary)">{{ localstack_url }}</a></td></tr>
    </table>
  </div>
</div>"""

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('index'))
    stats = {'buckets': 0, 'users': 0, 'my_files': 0, 'queue_msgs': '?'}
    try:
        stats['buckets'] = len(get_client('s3').list_buckets().get('Buckets', []))
    except: pass
    try:
        t = get_client('dynamodb').describe_table(TableName='users')
        stats['users'] = t['Table'].get('ItemCount', 0)
    except: pass
    try:
        s3 = get_client('s3')
        r = s3.list_objects_v2(Bucket=BUCKET, Prefix=session['username']+'/')
        stats['my_files'] = r.get('KeyCount', 0)
    except: pass
    try:
        q = get_client('sqs')
        qu = f"{LOCALSTACK_URL}/000000000000/order-processing-queue"
        a = q.get_queue_attributes(QueueUrl=qu, AttributeNames=['ApproximateNumberOfMessages'])
        stats['queue_msgs'] = a['Attributes'].get('ApproximateNumberOfMessages', '?')
    except: pass
    return render(DASHBOARD_CONTENT, page_title="Dashboard", active="dashboard",
                  stats=stats, config=CLOUD_CONFIG,
                  localstack_url=LOCALSTACK_URL, region=AWS_REGION)

# ─────────────────────────────────────────────────────────────────────────────
# CLOUD DRIVE  (real file upload, user-scoped, IDOR on share/download/delete)
# ─────────────────────────────────────────────────────────────────────────────
DRIVE_CONTENT = """
<div class="card">
  <div class="card-title"><i class="fas fa-cloud-arrow-up" style="color:var(--primary)"></i> Upload Files</div>
  <div class="card-sub">Upload any file type — stored in your personal S3 folder</div>
  <form action="/drive/upload" method="POST" enctype="multipart/form-data">
    <div class="drop-zone">
      <input type="file" name="file" id="file-input">
      <div class="dz-icon"><i class="fas fa-cloud-arrow-up"></i></div>
      <div class="dz-text">Click or drag a file here</div>
      <div class="dz-hint">Any file type supported · Your files are private to your account</div>
    </div>
    <button type="submit" class="btn btn-primary" style="margin-top:14px">
      <i class="fas fa-upload"></i> Upload to S3
    </button>
  </form>
</div>

<div class="card">
  <div class="card-title"><i class="fas fa-folder-open" style="color:var(--secondary)"></i> My Files
    <span class="badge badge-primary" style="margin-left:8px">{{ files|length }} objects</span>
  </div>
  <div class="card-sub">Files in your personal bucket folder: <code style="color:var(--primary)">s3://sensitive-data-bucket/{{ username }}/</code></div>
  {% if files %}
  <table>
    <thead><tr><th>File</th><th>Size</th><th>Modified</th><th>Actions</th></tr></thead>
    <tbody>
    {% for f in files %}
    <tr>
      <td>
        <i class="fas {{ f.icon }}" style="color:var(--primary);margin-right:8px;width:16px"></i>
        {{ f.name }}
      </td>
      <td style="color:var(--muted)">{{ f.size }}</td>
      <td style="color:var(--muted)">{{ f.modified }}</td>
      <td>
        <a href="/drive/download?key={{ f.key }}" class="btn btn-ghost btn-sm">
          <i class="fas fa-download"></i> Download
        </a>
        <a href="/drive/share?key={{ f.key }}" class="btn btn-success btn-sm" style="margin-left:6px">
          <i class="fas fa-share-nodes"></i> Share
        </a>
        <a href="/drive/delete?key={{ f.key }}" class="btn btn-danger btn-sm" style="margin-left:6px"
           onclick="return confirm('Delete this file?')">
          <i class="fas fa-trash"></i>
        </a>
      </td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div style="text-align:center;padding:40px;color:var(--muted)">
    <i class="fas fa-inbox" style="font-size:40px;margin-bottom:12px;display:block;opacity:.3"></i>
    No files yet — upload something above
  </div>
  {% endif %}
</div>

{% if shared_link %}
<div class="card" style="border-color:rgba(79,142,247,.3)">
  <div class="card-title"><i class="fas fa-link" style="color:var(--primary)"></i> Shareable Link Generated</div>
  <div class="card-sub">Valid for 1 hour. Share this pre-signed S3 URL:</div>
  <input type="text" value="{{ shared_link }}" readonly onclick="this.select();this.setSelectionRange(0,999999)"
         style="font-family:monospace;font-size:12px;cursor:pointer">
</div>
{% endif %}"""

@app.route("/drive")
def drive():
    if not session.get('logged_in'): return redirect(url_for('index'))
    files = []
    shared_link = request.args.get('shared_link')
    try:
        s3 = get_client('s3')
        prefix = session['username'] + '/'
        # Only list the current user's files — seeded attack files stay in bucket
        # but are only accessible via AWS CLI / SSRF exploitation (the intended attack path)
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
        for obj in resp.get('Contents', []):
            key  = obj['Key']
            name = key[len(prefix):]        # strip username/ prefix for display
            if not name: continue           # skip bare prefix entry
            files.append({
                'key':      key,
                'name':     name,
                'size':     fmt_size(obj['Size']),
                'modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M'),
                'icon':     file_icon(name)
            })
    except Exception as e:
        flash(f"S3 error: {str(e)}")
    return render(DRIVE_CONTENT, page_title="Cloud Drive", active="drive",
                  files=files, shared_link=shared_link,
                  username=session.get('username',''))

@app.route("/drive/upload", methods=["POST"])
def drive_upload():
    if not session.get('logged_in'): return redirect(url_for('index'))
    f = request.files.get('file')
    if not f or f.filename == '':
        flash("No file selected.")
        return redirect(url_for('drive'))
    key     = session['username'] + '/' + f.filename
    content = f.read()
    ctype   = f.content_type or mimetypes.guess_type(f.filename)[0] or 'application/octet-stream'
    try:
        get_client('s3').put_object(Bucket=BUCKET, Key=key, Body=content, ContentType=ctype)
        flash(f"'{f.filename}' uploaded successfully ({fmt_size(len(content))}).", "success")
    except Exception as e:
        flash(f"Upload failed: {str(e)}")
    return redirect(url_for('drive'))

@app.route("/drive/download")
def drive_download():
    if not session.get('logged_in'): return redirect(url_for('index'))
    key = request.args.get('key','')
    if not key: return redirect(url_for('drive'))
    try:
        s3    = get_client('s3')
        # Vulnerability: IDOR — no ownership check; any authenticated user can
        # download ANY key in the bucket, including the seeded sensitive files:
        # backups/credentials.csv, .env, keys/deploy_key.pem, exports/customer_pii.csv …
        obj   = s3.get_object(Bucket=BUCKET, Key=key)
        data  = obj['Body'].read()
        fname = key.split('/')[-1]
        ctype = obj.get('ContentType','application/octet-stream')
        return send_file(BytesIO(data), download_name=fname,
                         as_attachment=True, mimetype=ctype)
    except Exception as e:
        flash(f"Download failed: {str(e)}")
        return redirect(url_for('drive'))

@app.route("/drive/share")
def drive_share():
    if not session.get('logged_in'): return redirect(url_for('index'))
    key = request.args.get('key','')
    if not key: return redirect(url_for('drive'))
    try:
        s3  = get_client('s3')
        # Vulnerability: IDOR — no ownership check on share either
        url = s3.generate_presigned_url('get_object',
              Params={'Bucket': BUCKET, 'Key': key}, ExpiresIn=3600)
        # Rewrite internal hostname to be browser-accessible
        public_host = request.host.split(':')[0]
        url = url.replace(LOCALSTACK_URL, f"http://{public_host}:4566")
        return redirect(url_for('drive', shared_link=url))
    except Exception as e:
        flash(f"Share failed: {str(e)}")
        return redirect(url_for('drive'))

@app.route("/drive/delete")
def drive_delete():
    if not session.get('logged_in'): return redirect(url_for('index'))
    key = request.args.get('key','')
    if not key: return redirect(url_for('drive'))
    # Vulnerability: IDOR — can delete any file in the bucket, not just the user's own
    try:
        get_client('s3').delete_object(Bucket=BUCKET, Key=key)
        flash(f"File deleted.", "success")
    except Exception as e:
        flash(f"Delete failed: {str(e)}")
    return redirect(url_for('drive'))

# ─────────────────────────────────────────────────────────────────────────────
# ASYNC PROCESSING  (SQS + SNS)
# ─────────────────────────────────────────────────────────────────────────────
PROCESSING_CONTENT = """
<div class="grid-2">
  <div class="card">
    <div class="card-title"><i class="fas fa-layer-group" style="color:#fbbf24"></i> SQS — Job Queue</div>
    <div class="card-sub">Submit background jobs to the <code>order-processing-queue</code></div>
    <form action="/processing/sqs" method="POST">
      <div class="form-group"><label>Job Name / Task Description</label>
        <input type="text" name="task" placeholder="e.g. Generate monthly report" required>
      </div>
      <div class="form-group"><label>Priority</label>
        <select name="priority">
          <option value="low">🟢 Low</option>
          <option value="normal" selected>🟡 Normal</option>
          <option value="high">🔴 High</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary"><i class="fas fa-paper-plane"></i> Send to Queue</button>
    </form>
  </div>
  <div class="card">
    <div class="card-title"><i class="fas fa-bullhorn" style="color:var(--danger)"></i> SNS — Broadcast Alert</div>
    <div class="card-sub">Publish a message to the <code>security-alerts</code> topic</div>
    <form action="/processing/sns" method="POST">
      <div class="form-group"><label>Alert Message</label>
        <textarea name="message" rows="3" placeholder="Attention all staff..." required></textarea>
      </div>
      <div class="form-group"><label>Severity</label>
        <select name="severity">
          <option value="INFO">ℹ️  INFO</option>
          <option value="WARN">⚠️  WARNING</option>
          <option value="CRITICAL">🚨 CRITICAL</option>
        </select>
      </div>
      <button type="submit" class="btn btn-danger"><i class="fas fa-broadcast-tower"></i> Broadcast</button>
    </form>
  </div>
</div>"""

@app.route("/processing")
def processing():
    if not session.get('logged_in'): return redirect(url_for('index'))
    return render(PROCESSING_CONTENT, page_title="Async Processing", active="processing")

@app.route("/processing/sqs", methods=["POST"])
def sqs_send():
    if not session.get('logged_in'): return redirect(url_for('index'))
    task     = request.form.get("task","")
    priority = request.form.get("priority","normal")
    try:
        sqs  = get_client('sqs')
        qu   = f"{LOCALSTACK_URL}/000000000000/order-processing-queue"
        body = {"task": task, "priority": priority, "submitted_by": session['username']}
        r    = sqs.send_message(QueueUrl=qu, MessageBody=json.dumps(body))
        flash(f"Job sent to SQS queue! MessageId: {r['MessageId']}", "success")
    except Exception as e:
        flash(f"SQS Error: {str(e)}")
    return redirect(url_for('processing'))

@app.route("/processing/sns", methods=["POST"])
def sns_broadcast():
    if not session.get('logged_in'): return redirect(url_for('index'))
    msg      = request.form.get("message","")
    severity = request.form.get("severity","INFO")
    try:
        sns   = get_client('sns')
        topic = "arn:aws:sns:us-east-1:000000000000:security-alerts"
        body  = f"[{severity}] {session['username']}: {msg}"
        r     = sns.publish(TopicArn=topic, Message=body, Subject=f"CyberRange Alert — {severity}")
        flash(f"Alert broadcast via SNS! MessageId: {r.get('MessageId','N/A')}", "success")
    except Exception as e:
        flash(f"SNS Error: {str(e)}")
    return redirect(url_for('processing'))

# ─────────────────────────────────────────────────────────────────────────────
# SERVERLESS  (Lambda invocation)
# ─────────────────────────────────────────────────────────────────────────────
SERVERLESS_CONTENT = """
<div class="card">
  <div class="card-title"><i class="fas fa-code" style="color:var(--secondary)"></i> Invoke <code>vulnerable-api</code> Lambda</div>
  <div class="card-sub">Directly call the backend Lambda function via the AWS SDK — no API Gateway auth required</div>
  <form action="/serverless/invoke" method="POST">
    <div class="form-group"><label>Action</label>
      <select name="action" id="sel-action">
        <option value="get_user">get_user — Fetch user record from DynamoDB</option>
        <option value="list_files">list_files — List all files in S3 bucket</option>
      </select>
    </div>
    <div class="form-group" id="uid-group"><label>User ID</label>
      <input type="text" name="user_id" placeholder="USR001" id="uid-input">
      <div style="font-size:12px;color:var(--muted);margin-top:4px">
        Try: USR001, USR002, USR003, USR004, USR005 · Leave blank to trigger error disclosure
      </div>
    </div>
    <button type="submit" class="btn btn-primary"><i class="fas fa-play"></i> Invoke Lambda</button>
  </form>
</div>
{% if result %}
<div class="card">
  <div class="card-title"><i class="fas fa-terminal" style="color:var(--success)"></i> Lambda Response</div>
  <div class="terminal-bar">
    <span class="dot" style="background:#f87171"></span>
    <span class="dot" style="background:#fbbf24"></span>
    <span class="dot" style="background:#34d399"></span>
    <span style="margin-left:8px;font-size:12px;color:var(--muted)">lambda: vulnerable-api</span>
  </div>
  <div class="terminal">{{ result }}</div>
</div>
{% endif %}
<script>
document.getElementById('sel-action').addEventListener('change', function(){
  document.getElementById('uid-group').style.display = this.value==='get_user' ? 'block' : 'none';
});
</script>"""

@app.route("/serverless")
def serverless():
    if not session.get('logged_in'): return redirect(url_for('index'))
    return render(SERVERLESS_CONTENT, page_title="Serverless APIs", active="serverless", result=None)

@app.route("/serverless/invoke", methods=["POST"])
def serverless_invoke():
    if not session.get('logged_in'): return redirect(url_for('index'))
    action  = request.form.get("action","")
    user_id = request.form.get("user_id","")
    payload = {"body": json.dumps({"action": action, "user_id": user_id})}
    try:
        lc  = get_client('lambda')
        r   = lc.invoke(FunctionName='vulnerable-api', InvocationType='RequestResponse',
                        Payload=json.dumps(payload))
        out = json.loads(r['Payload'].read().decode())
        result = json.dumps(out, indent=2)
    except Exception as e:
        result = f"Lambda invocation error: {str(e)}"
    return render(SERVERLESS_CONTENT, page_title="Serverless APIs", active="serverless", result=result)

# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOKS  (SSRF target)
# ─────────────────────────────────────────────────────────────────────────────
WEBHOOKS_CONTENT = """
<div class="card">
  <div class="card-title"><i class="fas fa-link" style="color:var(--primary)"></i> Webhook Integration Test</div>
  <div class="card-sub">Test connectivity to external webhook endpoints. The server will fetch the URL and display the response.</div>
  <form action="/webhooks/test" method="POST">
    <div class="form-group"><label>Webhook URL</label>
      <!-- Vulnerability: SSRF — no URL validation -->
      <input type="text" name="url" placeholder="https://api.yourservice.com/ping" required>
    </div>
    <div class="form-group"><label>Example targets to try</label>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
        <button type="button" class="btn btn-ghost btn-sm" onclick="setUrl('http://metadata-service/latest/meta-data/')">🔍 IMDS Root</button>
        <button type="button" class="btn btn-ghost btn-sm" onclick="setUrl('http://metadata-service/latest/meta-data/iam/security-credentials/vulnerable-role')">🔑 IAM Credentials</button>
        <button type="button" class="btn btn-ghost btn-sm" onclick="setUrl('http://localstack:4566/_localstack/health')">☁️ LocalStack Health</button>
      </div>
    </div>
    <button type="submit" class="btn btn-primary"><i class="fas fa-arrow-right"></i> Send Request</button>
  </form>
</div>
{% if result %}
<div class="card">
  <div class="card-title"><i class="fas fa-terminal" style="color:var(--success)"></i> Server-Side Response</div>
  <div class="terminal-bar">
    <span class="dot" style="background:#f87171"></span>
    <span class="dot" style="background:#fbbf24"></span>
    <span class="dot" style="background:#34d399"></span>
    <span style="margin-left:8px;font-size:12px;color:var(--muted)">server-side fetch result</span>
  </div>
  <div class="terminal">{{ result }}</div>
</div>
{% endif %}
<script>
function setUrl(u){ document.querySelector('input[name=url]').value = u; }
</script>"""

@app.route("/webhooks")
def webhooks():
    if not session.get('logged_in'): return redirect(url_for('index'))
    return render(WEBHOOKS_CONTENT, page_title="Webhooks", active="webhooks", result=None)

@app.route("/webhooks/test", methods=["POST"])
def webhooks_test():
    if not session.get('logged_in'): return redirect(url_for('index'))
    url = request.form.get("url","")
    try:
        # Vulnerability: SSRF — fetches any URL including internal metadata endpoints
        resp   = http_requests.get(url, timeout=5)
        result = (f"HTTP {resp.status_code}  {resp.url}\n"
                  f"{'─'*60}\n"
                  + "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
                  + f"\n{'─'*60}\n{resp.text[:4000]}")
    except Exception as e:
        result = f"Connection failed: {str(e)}"
    return render(WEBHOOKS_CONTENT, page_title="Webhooks", active="webhooks", result=result)

# ─────────────────────────────────────────────────────────────────────────────
# API STATUS  (info-disclosure endpoint)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    # Vulnerability: exposes internal service topology + connection strings
    return jsonify({
        "status": "running", "app_version": "2.0.0",
        "active_features": ["dynamodb","s3","sqs","sns","kms","lambda"],
        "internal_services": {
            "metadata_endpoint": "http://metadata-service:80",
            "localstack_conn":   LOCALSTACK_URL
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)
