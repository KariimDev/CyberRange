"""
Vulnerable Web Application — CyberRange Target
Intentional vulnerabilities:
  1. SSRF via /fetch endpoint (fetches any user-supplied URL)
  2. Command Injection via /healthcheck endpoint
  3. Information Disclosure via /debug endpoint
"""

from flask import Flask, request, render_template_string, jsonify
import requests as http_requests
import subprocess
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Internal URL Fetcher</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; background: #1a1a2e; color: #eee; }
  h1 { color: #e94560; }
  input, button { padding: 10px; margin: 5px 0; border-radius: 6px; border: 1px solid #333; }
  input { width: 70%; background: #16213e; color: #eee; }
  button { background: #e94560; color: white; border: none; cursor: pointer; }
  pre { background: #16213e; padding: 15px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }
  .section { margin: 30px 0; padding: 20px; border: 1px solid #333; border-radius: 10px; }
</style>
</head>
<body>
  <h1>Internal URL Fetcher Tool</h1>
  <div class="section">
    <h3>Fetch a URL</h3>
    <form action="/fetch" method="POST">
      <input type="text" name="url" placeholder="https://example.com" />
      <button type="submit">Fetch</button>
    </form>
  </div>
  <div class="section">
    <h3>Health Check</h3>
    <form action="/healthcheck" method="GET">
      <input type="text" name="target" placeholder="hostname or IP" />
      <button type="submit">Ping</button>
    </form>
  </div>
  {% if result %}
  <div class="section">
    <h3>Result</h3>
    <pre>{{ result }}</pre>
  </div>
  {% endif %}
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/fetch", methods=["POST"])
def fetch_url():
    """VULNERABILITY: SSRF — fetches any URL including internal services"""
    url = request.form.get("url", "")
    if not url:
        return render_template_string(HTML_TEMPLATE, result="Error: No URL provided")
    try:
        resp = http_requests.get(url, timeout=5)
        return render_template_string(HTML_TEMPLATE, result=f"Status: {resp.status_code}\n\n{resp.text}")
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, result=f"Error: {str(e)}")

@app.route("/healthcheck")
def healthcheck():
    """VULNERABILITY: OS Command Injection via target parameter"""
    target = request.args.get("target", "localhost")
    try:
        result = subprocess.run(
            f"ping -c 1 {target}",
            shell=True, capture_output=True, text=True, timeout=5
        )
        output = result.stdout or result.stderr
        return render_template_string(HTML_TEMPLATE, result=output)
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, result=f"Error: {str(e)}")

@app.route("/debug")
def debug():
    """VULNERABILITY: Debug endpoint leaks environment variables"""
    env_vars = dict(os.environ)
    return jsonify({"environment": env_vars, "cwd": os.getcwd()})

@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "running",
        "version": "1.3.7",
        "internal_services": {
            "metadata": "http://metadata-service:80",
            "localstack": "http://localstack:4566",
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
