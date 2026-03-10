import os
import json
import uuid
import boto3
from botocore.config import Config
import requests as http_requests
from botocore.exceptions import ClientError
from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "nscs_gate_secure_session_key"

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL", "http://localstack:4566")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

def get_client(service):
    my_config = Config(
        connect_timeout=3,
        read_timeout=3,
        retries={'max_attempts': 1}
    )
    return boto3.client(
        service,
        endpoint_url=LOCALSTACK_URL,
        region_name=AWS_REGION,
        config=my_config
    )

# --- App Initialization: Load Config ---
def load_cloud_config():
    config = {}
    try:
        ssm = get_client('ssm')
        param = ssm.get_parameter(Name='/prod/app/config', WithDecryption=True)
        config['app_config'] = json.loads(param['Parameter']['Value'])
    except Exception as e:
        config['app_config_error'] = str(e)
    return config

CLOUD_CONFIG = load_cloud_config()

# --- HTML Templates ---
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<title>NSCS-Gate</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 40px auto; background: #0f172a; color: #f1f5f9; }
  h1 { color: #38bdf8; border-bottom: 2px solid #1e293b; padding-bottom: 10px; }
  h2, h3 { color: #7dd3fc; }
  .navbar { background: #1e293b; padding: 15px; border-radius: 5px; color: white; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; }
  .navbar div a { color: #38bdf8; text-decoration: none; margin-right: 15px; font-weight: bold; }
  .navbar a:hover { color: #bae6fd; }
  .card { background: #1e293b; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; border: 1px solid #334155; }
  input[type="text"], input[type="password"], textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #475569; border-radius: 4px; box-sizing: border-box; background: #0f172a; color: white; }
  button { background: #0284c7; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }
  button:hover { background: #0369a1; }
  .alert { padding: 15px; background-color: #991b1b; color: white; margin-bottom: 20px; border-radius: 4px; border: 1px solid #f87171; }
  .success { padding: 15px; background-color: #166534; color: white; margin-bottom: 20px; border-radius: 4px; border: 1px solid #4ade80; }
  pre { background: #0f172a; padding: 15px; border-radius: 4px; overflow-x: auto; border: 1px solid #334155; color: #a7f3d0; }
  a.btn { display: inline-block; background: #0284c7; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 14px; }
  a.btn:hover { background: #0369a1; }
  ul { list-style-type: none; padding: 0; }
  li { background: #334155; margin-bottom: 10px; padding: 15px; border-radius: 4px; }
</style>
</head>
<body>
  <h1>NSCS-Gate Cloud Platform</h1>
  
  <div class="navbar">
    <div>
      {% if session.get('logged_in') %}
        <span style="margin-right: 20px; color: #94a3b8;">User: <strong>{{ session.get('username') }}</strong></span>
        <a href="/dashboard">Dashboard</a>
        <a href="/drive">Cloud Drive</a>
        <a href="/processing">Async Processing</a>
        <a href="/serverless">Serverless APIs</a>
        <a href="/webhooks">Webhooks</a>
      {% else %}
        <a href="/">Login</a>
        <a href="/register">Sign Up</a>
      {% endif %}
    </div>
    <div>
      {% if session.get('logged_in') %}
        <a href="/logout">Logout</a>
      {% endif %}
    </div>
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="{{ 'success' if category == 'success' else 'alert' }}">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {% block content %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card" style="max-width: 400px; margin: 0 auto;">
  <h2>Sign In</h2>
  <form action="/login" method="POST">
    <label>Username</label>
    <input type="text" name="username" required />
    <label>Password</label>
    <input type="password" name="password" required />
    <button type="submit" style="width: 100%; margin-top: 10px;">Sign In</button>
  </form>
  <p style="text-align: center; margin-top: 15px; color: #94a3b8;">Don't have an account? <a href="/register" style="color: #38bdf8;">Sign up</a></p>
</div>
""")

REGISTER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card" style="max-width: 400px; margin: 0 auto;">
  <h2>Create Account</h2>
  <form action="/register" method="POST">
    <label>Username</label>
    <input type="text" name="username" required />
    <label>Email</label>
    <input type="text" name="email" required />
    <label>Password</label>
    <input type="password" name="password" required />
    <button type="submit" style="width: 100%; margin-top: 10px; background: #166534;">Sign Up (DynamoDB)</button>
  </form>
</div>
""")

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card">
  <h2>Welcome to NSCS-Gate Dashboard</h2>
  <p>Your cloud environment is active. Here is the configuration loaded from <strong>AWS Systems Manager (SSM)</strong>:</p>
  <pre>{{ config_dump }}</pre>
</div>
""")

DRIVE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card">
  <h2>Cloud Drive (S3 Integration)</h2>
  <p>Upload files securely to AWS S3. You can generate a shareable link for downloaded files.</p>
  
  <form action="/drive/upload" method="POST" style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #475569;">
    <label>Filename (e.g., project.txt)</label>
    <input type="text" name="filename" required />
    <label>File Content</label>
    <textarea name="content" rows="4" required></textarea>
    <button type="submit">Upload to S3</button>
  </form>
  
  <h3>Your Files</h3>
  <ul>
    {% for file in files %}
      <li>
        <strong>{{ file.key }}</strong> 
        <span style="color: #94a3b8; font-size: 0.9em;">(Size: {{ file.size }} bytes)</span>
        <br/><br/>
        <a href="/drive/share?key={{ file.key }}" class="btn">Generate Shareable Link</a>
      </li>
    {% else %}
      <li>No files found in the bucket.</li>
    {% endfor %}
  </ul>
  
  {% if shared_link %}
    <div style="margin-top: 20px; padding: 15px; background: #0f172a; border-radius: 5px; border: 1px dashed #38bdf8;">
      <h4>Shareable Link (Valid for 1 hour):</h4>
      <input type="text" value="{{ shared_link }}" readonly onclick="this.select();" />
    </div>
  {% endif %}
</div>
""")

PROCESSING_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card">
  <h2>Async Data Processing (SQS & SNS Integration)</h2>
  <p>Submit a background job to the SQS queue, and optionally broadcast a notification via SNS.</p>
  
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
    <div style="padding: 15px; border: 1px solid #334155; border-radius: 5px;">
      <h3>1. Submit Job to SQS</h3>
      <form action="/processing/sqs" method="POST">
        <label>Job Name / Task</label>
        <input type="text" name="task" placeholder="e.g., Generate Monthly Report" required />
        <button type="submit">Send to Queue</button>
      </form>
    </div>
    
    <div style="padding: 15px; border: 1px solid #334155; border-radius: 5px;">
      <h3>2. Broadcast via SNS</h3>
      <form action="/processing/sns" method="POST">
        <label>Announcement Message</label>
        <input type="text" name="message" placeholder="Attention all staff..." required />
        <button type="submit" style="background: #991b1b;">Broadcast Alert</button>
      </form>
    </div>
  </div>
</div>
""")

SERVERLESS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card">
  <h2>Serverless Data API (Lambda Integration)</h2>
  <p>Invoke the backend AWS Lambda function directly to retrieve user data or list internal files.</p>
  
  <form action="/serverless/invoke" method="POST">
    <label>Select Action</label>
    <select name="action" style="width: 100%; padding: 10px; margin: 8px 0; background: #0f172a; border: 1px solid #475569; color: white; border-radius: 4px;">
      <option value="get_user">Get User Details (DynamoDB via Lambda)</option>
      <option value="list_files">List All Cloud Files (S3 via Lambda)</option>
    </select>
    
    <label>User ID (only for 'Get User Details', e.g., USR001)</label>
    <input type="text" name="user_id" placeholder="USR001" />
    
    <button type="submit">Invoke Lambda Function</button>
  </form>
  
  {% if lambda_result %}
    <h3 style="margin-top: 30px;">Lambda Response:</h3>
    <pre>{{ lambda_result }}</pre>
  {% endif %}
</div>
""")

WEBHOOKS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card">
  <h2>Webhook Integrations</h2>
  <p>Test external webhook endpoints to integrate NSCS-Gate with third-party services.</p>
  <form action="/webhooks/test" method="POST">
    <label>Webhook URL</label>
    <!-- Vulnerability: SSRF -->
    <input type="text" name="url" placeholder="http://api.externalcorp.com/ping" required />
    <button type="submit">Test Connection</button>
  </form>
  
  {% if webhook_result %}
    <h3 style="margin-top: 30px;">Response:</h3>
    <pre>{{ webhook_result }}</pre>
  {% endif %}
</div>
""")

# --- Routes ---

@app.route("/")
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template_string(REGISTER_TEMPLATE)
        
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    # BUG FIX: uuid.uuid4() returns a string like "550e8400-e29b-41d4-a716-446655440000".
    # Slicing [:6] includes the dashes (e.g. "550e84"), and uppercasing it produced IDs
    # that could look like "USR550E84" but with only 6 hex chars (low entropy) risked
    # colliding with seeded IDs (USR001, USR002, ...). Use hex without dashes for safety.
    user_id = "USR" + uuid.uuid4().hex[:6].upper()
    
    try:
        dynamodb = get_client('dynamodb')
        dynamodb.put_item(
            TableName="users",
            Item={
                'user_id': {'S': user_id},
                'username': {'S': username},
                'email': {'S': email},
                'password': {'S': password},
                'role': {'S': 'user'}
            }
        )
        flash("Account created successfully in DynamoDB! You can now log in.", "success")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"DynamoDB Error: {str(e)}")
        return redirect(url_for('register'))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    
    try:
        dynamodb = get_client('dynamodb')
        # Vulnerability: Scanning full table to auth (allows enumeration)
        response = dynamodb.scan(TableName="users")
        
        user_record = None
        for item in response.get('Items', []):
            if item.get('username', {}).get('S') == username:
                user_record = item
                break
                
        if user_record and user_record.get('password', {}).get('S') == password:
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user_record.get('user_id', {}).get('S', '')
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!")
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f"Database error: {str(e)}")
        return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('index'))
    config = load_cloud_config()
    return render_template_string(DASHBOARD_TEMPLATE, config_dump=json.dumps(config, indent=2))

@app.route("/drive")
def drive():
    if not session.get('logged_in'): return redirect(url_for('index'))
    s3 = get_client('s3')
    bucket = "sensitive-data-bucket"
    
    shared_link = request.args.get('shared_link')
    
    files = []
    try:
        resp = s3.list_objects_v2(Bucket=bucket)
        if 'Contents' in resp:
            for obj in resp['Contents']:
                files.append({"key": obj['Key'], "size": obj['Size']})
    except Exception as e:
        flash(f"Error fetching files from S3: {str(e)}")
        
    return render_template_string(DRIVE_TEMPLATE, files=files, shared_link=shared_link)

@app.route("/drive/upload", methods=["POST"])
def drive_upload():
    if not session.get('logged_in'): return redirect(url_for('index'))
    filename = request.form.get("filename")
    content = request.form.get("content")
    prefix = session.get('username') + "/"
    key = prefix + filename
    
    try:
        s3 = get_client('s3')
        s3.put_object(Bucket="sensitive-data-bucket", Key=key, Body=content.encode())
        flash(f"File uploaded to S3: {key}", "success")
    except Exception as e:
        flash(f"S3 Upload failed: {str(e)}")
        
    return redirect(url_for('drive'))

@app.route("/drive/share", methods=["GET"])
def drive_share():
    if not session.get('logged_in'): return redirect(url_for('index'))
    key = request.args.get("key")
    if not key: return redirect(url_for('drive'))
    
    try:
        s3 = get_client('s3')
        # Generate presigned URL
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': 'sensitive-data-bucket', 'Key': key},
            ExpiresIn=3600 # 1 hour
        )
        # BUG FIX: LocalStack generates presigned URLs using its internal Docker hostname
        # (e.g. http://localstack:4566/...) which is unreachable from the user's browser.
        # We rewrite the host portion to localhost:4566 so the link actually works.
        public_host = request.host.split(':')[0]  # e.g. "localhost"
        url = url.replace(LOCALSTACK_URL, f"http://{public_host}:4566")
        return redirect(url_for('drive', shared_link=url))
    except Exception as e:
        flash(f"Failed to generate link: {str(e)}")
        return redirect(url_for('drive'))

@app.route("/processing")
def processing():
    if not session.get('logged_in'): return redirect(url_for('index'))
    return render_template_string(PROCESSING_TEMPLATE)

@app.route("/processing/sqs", methods=["POST"])
def sqs_job():
    if not session.get('logged_in'): return redirect(url_for('index'))
    task = request.form.get("task")
    try:
        sqs = get_client('sqs')
        # BUG FIX: Was hardcoded to "localhost" which resolves to the container itself,
        # not LocalStack. Must use LOCALSTACK_URL env var (http://localstack:4566).
        queue_url = f"{LOCALSTACK_URL}/000000000000/order-processing-queue"
        payload = {"task": task, "submitted_by": session.get('username')}
        response = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
        flash(f"Task successfully pushed to SQS! MessageId: {response['MessageId']}", "success")
    except Exception as e:
        flash(f"SQS Error: {str(e)}")
    return redirect(url_for('processing'))

@app.route("/processing/sns", methods=["POST"])
def sns_alert():
    if not session.get('logged_in'): return redirect(url_for('index'))
    msg = request.form.get("message")
    try:
        sns = get_client('sns')
        topic_arn = "arn:aws:sns:us-east-1:000000000000:security-alerts"
        response = sns.publish(TopicArn=topic_arn, Message=f"[{session.get('username')}]: {msg}")
        # BUG FIX: boto3 publish() returns {'MessageId': '...', 'ResponseMetadata': {...}}
        # Use direct key access with a fallback to avoid showing "None" in the flash message.
        flash(f"Alert broadcasted via SNS! MessageId: {response.get('MessageId', 'N/A')}", "success")
    except Exception as e:
        flash(f"SNS Error: {str(e)}")
    return redirect(url_for('processing'))

@app.route("/serverless")
def serverless():
    if not session.get('logged_in'): return redirect(url_for('index'))
    return render_template_string(SERVERLESS_TEMPLATE)

@app.route("/serverless/invoke", methods=["POST"])
def serverless_invoke():
    if not session.get('logged_in'): return redirect(url_for('index'))
    action = request.form.get("action")
    user_id = request.form.get("user_id", "")
    
    payload = {
        "body": json.dumps({
            "action": action,
            "user_id": user_id
        })
    }
    
    try:
        lambda_client = get_client('lambda')
        response = lambda_client.invoke(
            FunctionName='vulnerable-api',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        response_payload = json.loads(response['Payload'].read().decode("utf-8"))
        
        # Pretty print response
        output = json.dumps(response_payload, indent=2)
    except Exception as e:
        output = f"Lambda Invocation Error: {str(e)}"
        
    return render_template_string(SERVERLESS_TEMPLATE, lambda_result=output)

@app.route("/webhooks")
def webhooks():
    if not session.get('logged_in'): return redirect(url_for('index'))
    return render_template_string(WEBHOOKS_TEMPLATE)

@app.route("/webhooks/test", methods=["POST"])
def webhooks_test():
    if not session.get('logged_in'): return redirect(url_for('index'))
    url = request.form.get("url")
    # Vulnerability: SSRF
    try:
        resp = http_requests.get(url, timeout=5)
        output = f"Status Code: {resp.status_code}\n\nHeaders:\n{resp.headers}\n\nBody:\n{resp.text}"
    except Exception as e:
        output = f"Connection Failed: {str(e)}"
        
    return render_template_string(WEBHOOKS_TEMPLATE, webhook_result=output)

@app.route("/api/status")
def api_status():
    # Vulnerability: Leaks internal service endpoints
    return jsonify({
        "status": "running",
        "app_version": "2.0.0",
        "active_features": ["dynamodb", "s3", "sqs", "sns", "kms", "lambda_invoke"],
        "internal_services": {
            "metadata_endpoint": "http://metadata-service:80",
            "localstack_conn": LOCALSTACK_URL
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)
