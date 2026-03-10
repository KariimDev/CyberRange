#!/bin/bash
# ============================================================
# CyberRange — Vulnerability Restore Script (vulner.sh)
# Reverts ALL hardening patches — restores intentional vulns.
# Run this to switch to RED TEAM / training mode.
# ============================================================
# Usage: sudo bash scripts/vulner.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
APP="$ROOT/vulnerable-app/app.py"
LAMBDA="$ROOT/lambda/handler.py"
TF="$ROOT/main.tf"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${RED}${BOLD}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   ⚠️  CyberRange — Restoring Vulnerabilities   ║"
echo "  ║       (Use only in isolated lab environments)  ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# Guard: detect if already in vulnerable mode
if grep -q 'Vulnerability: SSRF' "$APP" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  App already appears to be in vulnerable mode. Run fix.sh first to harden.${NC}"
    exit 0
fi

# ── REVERT 1: app.py — Session Secret Key ─────────────────────
echo -e "${YELLOW}[1/7] Restoring weak session secret key...${NC}"
python3 - "$APP" << 'PYEOF'
import sys, re
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Remove the random key line (replace any variation of os.urandom(...) key)
c = re.sub(
    r"app\.secret_key = os\.urandom\(32\)\.hex\(\).*\n",
    'app.secret_key = "nscs_gate_secure_session_key"\n',
    c
)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Weak static session key restored")
PYEOF

# ── REVERT 2: app.py — SSRF protection ────────────────────────
echo -e "${YELLOW}[2/7] Removing SSRF protection from /webhooks/test...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

OLD = '''    # HARDENED: SSRF protection — block requests to cloud metadata & internal addresses
    from urllib.parse import urlparse as _urlparse
    _BLOCKED_HOSTS = {
        'localhost', '127.0.0.1', '0.0.0.0',
        '169.254.169.254',   # AWS/GCP IMDS
        'metadata-service',   # internal container
        'localstack',         # internal container
    }
    _BLOCKED_PREFIXES = ('10.', '172.', '192.168.')
    try:
        _parsed = _urlparse(url)
        _scheme = _parsed.scheme.lower()
        _host = (_parsed.hostname or '').lower()
        if (_scheme not in ('http', 'https')
                or _host in _BLOCKED_HOSTS
                or any(_host.startswith(p) for p in _BLOCKED_PREFIXES)):
            output = "Error: Requests to internal, metadata, or non-HTTP addresses are not permitted."
        else:
            resp = http_requests.get(url, timeout=5, allow_redirects=False)
            # HARDENED: Return only status code — do not echo full body/headers (info disclosure)
            output = f"Status Code: {resp.status_code}"
    except Exception as e:
        output = f"Connection Failed: {str(e)}"'''

NEW = '''    # Vulnerability: SSRF
    try:
        resp = http_requests.get(url, timeout=5)
        output = f"Status Code: {resp.status_code}\\n\\nHeaders:\\n{resp.headers}\\n\\nBody:\\n{resp.text}"
    except Exception as e:
        output = f"Connection Failed: {str(e)}"'''

c = c.replace(OLD, NEW)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ SSRF protection removed (endpoint unrestricted)")
PYEOF

# ── REVERT 3: app.py — Info Disclosure in /api/status ─────────
echo -e "${YELLOW}[3/7] Restoring internal service info leak in /api/status...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

OLD = '''    # HARDENED: Internal service topology not exposed
    return jsonify({
        "status": "running",
        "app_version": "2.0.0"
    })'''

NEW = '''    # Vulnerability: Leaks internal service endpoints
    return jsonify({
        "status": "running",
        "app_version": "2.0.0",
        "active_features": ["dynamodb", "s3", "sqs", "sns", "kms", "lambda_invoke"],
        "internal_services": {
            "metadata_endpoint": "http://metadata-service:80",
            "localstack_conn": LOCALSTACK_URL
        }
    })'''

c = c.replace(OLD, NEW)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Internal service info leak restored in /api/status")
PYEOF

# ── REVERT 4: app.py — IDOR check ─────────────────────────────
echo -e "${YELLOW}[4/7] Removing IDOR ownership check from /drive/share...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

OLD = '''    # HARDENED: IDOR fix — verify the requesting user actually owns this file.
    # All uploads are stored under username/ prefix (see drive_upload).
    _expected_prefix = session.get('username', '') + '/'
    if not key.startswith(_expected_prefix):
        flash("Access denied: you do not own this file.")
        return redirect(url_for('drive'))

    try:
        s3 = get_client('s3')
        # Generate presigned URL'''

NEW = '''    try:
        s3 = get_client('s3')
        # Generate presigned URL'''

c = c.replace(OLD, NEW)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ IDOR ownership check removed (any key accessible via /drive/share)")
PYEOF

# ── REVERT 5: app.py — Password hashing ───────────────────────
echo -e "${YELLOW}[5/7] Restoring plaintext password storage...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Remove sentinel + hashlib import
c = c.replace('import hashlib\nHARDENED_MODE = True  # sentinel — do not remove\n', '')
c = c.replace('import hashlib\n', '')

# Restore plaintext password store in register
c = c.replace(
    "                'password': {'S': hashlib.sha256(password.encode()).hexdigest()},  # HARDENED: hashed",
    "                'password': {'S': password},"
)

# Restore plaintext comparison in login
c = c.replace(
    "        _pw_hash = hashlib.sha256(password.encode()).hexdigest()\n"
    "        if user_record and user_record.get('password', {}).get('S') == _pw_hash:  # HARDENED: compare hash",
    "        if user_record and user_record.get('password', {}).get('S') == password:"
)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Plaintext password storage restored")
PYEOF

# ── REVERT 6: lambda/handler.py ───────────────────────────────
echo -e "${YELLOW}[6/7] Restoring Lambda vulnerabilities...${NC}"
python3 - "$LAMBDA" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Restore hardcoded credentials
c = c.replace(
    '# HARDENED: Credentials sourced from environment variables — no hardcoded secrets\n'
    'AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "")\n'
    'AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")\n'
    'DB_PASSWORD = os.environ.get("DB_PASSWORD", "")\n'
    'API_TOKEN = os.environ.get("API_TOKEN", "")',

    '# ============================================\n'
    '# VULNERABILITY: Hardcoded secrets in code\n'
    '# A real developer mistake - credentials should\n'
    '# NEVER be hardcoded in source code\n'
    '# ============================================\n'
    'AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
    'AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
    'DB_PASSWORD = "SuperSecret123!"\n'
    'API_TOKEN = "sk-proj-abc123def456ghi789"'
)

# Re-enable debug mode
c = c.replace(
    '# HARDENED: Debug mode disabled\nDEBUG_MODE = False',
    '# Another vulnerability: debug mode left on in production\nDEBUG_MODE = True'
)

# Restore secret-leaking error response
c = c.replace(
    '    except Exception as e:\n'
    '        # HARDENED: Generic error — no sensitive debug info exposed to client\n'
    '        return {\n'
    '            "statusCode": 500,\n'
    '            "body": json.dumps({"error": "Internal server error. Contact your administrator."})\n'
    '        }',

    '    except Exception as e:\n'
    '        # VULNERABILITY: Leaking internal error details to the client\n'
    '        return {\n'
    '            "statusCode": 500,\n'
    '            "body": json.dumps({\n'
    '                "error": str(e),\n'
    '                "debug_info": {\n'
    '                    "db_password": DB_PASSWORD,\n'
    '                    "aws_key": AWS_ACCESS_KEY,\n'
    '                    "environment": dict(os.environ)\n'
    '                }\n'
    '            }, default=str)\n'
    '        }'
)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Hardcoded credentials restored")
print("  ✔ Debug mode re-enabled (sensitive log output active)")
print("  ✔ Error response restored (leaks DB_PASSWORD, AWS keys, env vars)")
PYEOF

# ── REVERT 7: main.tf ──────────────────────────────────────────
echo -e "${YELLOW}[7/7] Restoring vulnerable cloud infrastructure policies...${NC}"
python3 - "$TF" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# S3 public bucket: restore Allow
c = c.replace(
    '      Sid       = "PublicReadAccess"\n'
    '      Effect    = "Deny"  # HARDENED: public access blocked\n'
    '      Principal = "*"',
    '      Sid       = "PublicReadAccess"\n'
    '      Effect    = "Allow"\n'
    '      Principal = "*"'
)

# IAM: restore wildcard Action = "*"
c = c.replace(
    '      Effect   = "Allow"  # HARDENED: reduced to read-only\n'
    '      Action   = ["sts:GetCallerIdentity"]\n'
    '      Resource = "*"',
    '      Effect   = "Allow"\n'
    '      Action   = "*"\n'
    '      Resource = "*"'
)

# SQS: restore public access
c = c.replace(
    '      Action    = ["sqs:GetQueueAttributes"]  # HARDENED: public send/receive removed',
    '      Action    = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]'
)

# SNS: restore public access
c = c.replace(
    '      Action    = ["sns:GetTopicAttributes"]  # HARDENED: public subscribe/publish removed',
    '      Action    = ["sns:Subscribe", "sns:Publish", "sns:GetTopicAttributes"]'
)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ S3 public bucket policy → ALLOW restored")
print("  ✔ IAM wildcard Action=* restored")
print("  ✔ SQS public SendMessage/ReceiveMessage restored")
print("  ✔ SNS public Subscribe/Publish restored")
PYEOF

# ── Restore plaintext passwords in DynamoDB ────────────────────
echo -e "${YELLOW}[+] Restoring plaintext passwords in DynamoDB seeded users...${NC}"
python3 - << 'PYEOF'
import subprocess, json

ENDPOINT = "http://localhost:4566"
REGION   = "us-east-1"

users = [
    ("USR001", "P@ssw0rd123!"),
    ("USR002", "Welcome1!"),
    ("USR003", "Summer2026!"),
    ("USR004", "Qwerty789"),
]

for uid, pw in users:
    result = subprocess.run([
        "aws", "--endpoint-url", ENDPOINT, "--region", REGION,
        "dynamodb", "update-item",
        "--table-name", "users",
        "--key", json.dumps({"user_id": {"S": uid}}),
        "--update-expression", "SET #pw = :p",
        "--expression-attribute-names", json.dumps({"#pw": "password"}),
        "--expression-attribute-values", json.dumps({":p": {"S": pw}})
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✔ {uid} — plaintext password restored")
    else:
        print(f"  ⚠ {uid} — skipped (LocalStack may not be running: {result.stderr.strip()})")
PYEOF

# ── Rebuild & restart the app ──────────────────────────────────
echo ""
echo -e "${YELLOW}[+] Rebuilding vulnerable-app container...${NC}"
cd "$ROOT"
docker compose build vulnerable-app
docker compose up -d vulnerable-app

echo ""
echo -e "${RED}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║  ⚠️   NSCS-Gate is now running in VULNERABLE mode    ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  Vulnerabilities restored:                           ║"
echo "  ║    [app.py]   Weak static session secret             ║"
echo "  ║    [app.py]   SSRF — any URL (incl. IMDS) reachable  ║"
echo "  ║    [app.py]   /api/status leaks internal endpoints   ║"
echo "  ║    [app.py]   IDOR — any S3 key accessible           ║"
echo "  ║    [app.py]   Passwords stored in plaintext          ║"
echo "  ║    [lambda]   Hardcoded AWS/DB credentials           ║"
echo "  ║    [lambda]   DB password logged + leaked in errors  ║"
echo "  ║    [main.tf]  S3/IAM/SQS/SNS fully public            ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  ⚠  Use in ISOLATED lab environments only!           ║"
echo "  ║  ⚠  Run 'terraform apply' to apply infra changes     ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
