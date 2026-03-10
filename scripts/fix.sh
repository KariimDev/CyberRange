#!/bin/bash
# ============================================================
# CyberRange — Security Hardening Script (fix.sh)
# Patches ALL intentional vulnerabilities in the NSCS-Gate.
# Run this to switch to BLUE TEAM / hardened mode.
# ============================================================
# Usage: sudo bash scripts/fix.sh

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

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   🔒 CyberRange — Applying Hardening Patches  ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# Guard: detect if already hardened
if grep -q 'HARDENED_MODE = True' "$APP" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  App already appears to be in hardened mode. Run vulner.sh first to reset.${NC}"
    exit 0
fi

# ── PATCH 1: app.py — Session Secret Key ──────────────────────
echo -e "${YELLOW}[1/7] Hardening session secret key...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

c = c.replace(
    'app.secret_key = "nscs_gate_secure_session_key"',
    'app.secret_key = os.urandom(32).hex()  # HARDENED: cryptographically random, regenerated on restart'
)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Session key hardened")
PYEOF

# ── PATCH 2: app.py — SSRF in /webhooks/test ──────────────────
echo -e "${YELLOW}[2/7] Adding SSRF protection to /webhooks/test...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

OLD = '''    # Vulnerability: SSRF
    try:
        resp = http_requests.get(url, timeout=5)
        output = f"Status Code: {resp.status_code}\\n\\nHeaders:\\n{resp.headers}\\n\\nBody:\\n{resp.text}"
    except Exception as e:
        output = f"Connection Failed: {str(e)}"'''

NEW = '''    # HARDENED: SSRF protection — block requests to cloud metadata & internal addresses
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

c = c.replace(OLD, NEW)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ SSRF protection added")
PYEOF

# ── PATCH 3: app.py — Info Disclosure in /api/status ──────────
echo -e "${YELLOW}[3/7] Removing internal service info from /api/status...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

OLD = '''    # Vulnerability: Leaks internal service endpoints
    return jsonify({
        "status": "running",
        "app_version": "2.0.0",
        "active_features": ["dynamodb", "s3", "sqs", "sns", "kms", "lambda_invoke"],
        "internal_services": {
            "metadata_endpoint": "http://metadata-service:80",
            "localstack_conn": LOCALSTACK_URL
        }
    })'''

NEW = '''    # HARDENED: Internal service topology not exposed
    return jsonify({
        "status": "running",
        "app_version": "2.0.0"
    })'''

c = c.replace(OLD, NEW)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Internal service info removed from /api/status")
PYEOF

# ── PATCH 4: app.py — IDOR in /drive/share ────────────────────
echo -e "${YELLOW}[4/7] Adding IDOR ownership check to /drive/share...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

OLD = '''    try:
        s3 = get_client('s3')
        # Generate presigned URL'''

NEW = '''    # HARDENED: IDOR fix — verify the requesting user actually owns this file.
    # All uploads are stored under username/ prefix (see drive_upload).
    _expected_prefix = session.get('username', '') + '/'
    if not key.startswith(_expected_prefix):
        flash("Access denied: you do not own this file.")
        return redirect(url_for('drive'))

    try:
        s3 = get_client('s3')
        # Generate presigned URL'''

# Replace only the first occurrence (in drive_share, not other routes)
c = c.replace(OLD, NEW, 1)
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ IDOR ownership check added to /drive/share")
PYEOF

# ── PATCH 5: app.py — Plaintext Passwords ─────────────────────
echo -e "${YELLOW}[5/7] Enabling password hashing (SHA-256)...${NC}"
python3 - "$APP" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Add import if missing
if 'import hashlib' not in c:
    c = c.replace('import os\n', 'import os\nimport hashlib\n')

# Mark hardened mode sentinel for idempotency guard
c = c.replace('import hashlib\n', 'import hashlib\nHARDENED_MODE = True  # sentinel — do not remove\n', 1)

# Hash on register
c = c.replace(
    "                'password': {'S': password},",
    "                'password': {'S': hashlib.sha256(password.encode()).hexdigest()},  # HARDENED: hashed"
)

# Hash on login comparison
c = c.replace(
    "        if user_record and user_record.get('password', {}).get('S') == password:",
    "        _pw_hash = hashlib.sha256(password.encode()).hexdigest()\n"
    "        if user_record and user_record.get('password', {}).get('S') == _pw_hash:  # HARDENED: compare hash"
)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Password hashing enabled (SHA-256)")
PYEOF

# ── PATCH 6: lambda/handler.py — Hardcoded creds + info leak ──
echo -e "${YELLOW}[6/7] Hardening Lambda function...${NC}"
python3 - "$LAMBDA" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Remove hardcoded credentials — read from environment instead
c = c.replace(
    '# ============================================\n'
    '# VULNERABILITY: Hardcoded secrets in code\n'
    '# A real developer mistake - credentials should\n'
    '# NEVER be hardcoded in source code\n'
    '# ============================================\n'
    'AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
    'AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
    'DB_PASSWORD = "SuperSecret123!"\n'
    'API_TOKEN = "sk-proj-abc123def456ghi789"',

    '# HARDENED: Credentials sourced from environment variables — no hardcoded secrets\n'
    'AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "")\n'
    'AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")\n'
    'DB_PASSWORD = os.environ.get("DB_PASSWORD", "")\n'
    'API_TOKEN = os.environ.get("API_TOKEN", "")'
)

# Disable debug mode (stops sensitive log output)
c = c.replace(
    '# Another vulnerability: debug mode left on in production\nDEBUG_MODE = True',
    '# HARDENED: Debug mode disabled\nDEBUG_MODE = False'
)

# Sanitize the error response — remove debug_info block with secrets
c = c.replace(
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
    '        }',

    '    except Exception as e:\n'
    '        # HARDENED: Generic error — no sensitive debug info exposed to client\n'
    '        return {\n'
    '            "statusCode": 500,\n'
    '            "body": json.dumps({"error": "Internal server error. Contact your administrator."})\n'
    '        }'
)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ Hardcoded credentials removed")
print("  ✔ Debug mode disabled (sensitive log output suppressed)")
print("  ✔ Error response sanitized (no secrets leaked)")
PYEOF

# ── PATCH 7: main.tf — Cloud infrastructure policies ──────────
echo -e "${YELLOW}[7/7] Hardening Terraform cloud policies...${NC}"
python3 - "$TF" << 'PYEOF'
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# S3 public bucket: flip public Allow → Deny
c = c.replace(
    '      Sid       = "PublicReadAccess"\n'
    '      Effect    = "Allow"\n'
    '      Principal = "*"',
    '      Sid       = "PublicReadAccess"\n'
    '      Effect    = "Deny"  # HARDENED: public access blocked\n'
    '      Principal = "*"'
)

# IAM wildcard Action = "*" → least-privilege (both overly_permissive + admin_full_access policies)
c = c.replace(
    '      Effect   = "Allow"\n      Action   = "*"\n      Resource = "*"',
    '      Effect   = "Allow"  # HARDENED: reduced to read-only\n'
    '      Action   = ["sts:GetCallerIdentity"]\n'
    '      Resource = "*"'
)

# SQS public policy: remove SendMessage/ReceiveMessage/DeleteMessage
c = c.replace(
    '      Action    = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]',
    '      Action    = ["sqs:GetQueueAttributes"]  # HARDENED: public send/receive removed'
)

# SNS public policy: remove Subscribe/Publish
c = c.replace(
    '      Action    = ["sns:Subscribe", "sns:Publish", "sns:GetTopicAttributes"]',
    '      Action    = ["sns:GetTopicAttributes"]  # HARDENED: public subscribe/publish removed'
)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
print("  ✔ S3 public bucket policy → DENY")
print("  ✔ IAM wildcard Action=* → least-privilege")
print("  ✔ SQS public send/receive → removed")
print("  ✔ SNS public subscribe/publish → removed")
PYEOF

# ── Update seeded DynamoDB users with hashed passwords ─────────
echo -e "${YELLOW}[+] Updating seeded DynamoDB users to hashed passwords...${NC}"
python3 - << 'PYEOF'
import hashlib, subprocess, json

ENDPOINT = "http://localhost:4566"
REGION   = "us-east-1"

users = [
    ("USR001", "P@ssw0rd123!"),
    ("USR002", "Welcome1!"),
    ("USR003", "Summer2026!"),
    ("USR004", "Qwerty789"),
]

for uid, pw in users:
    hashed = hashlib.sha256(pw.encode()).hexdigest()
    result = subprocess.run([
        "aws", "--endpoint-url", ENDPOINT, "--region", REGION,
        "dynamodb", "update-item",
        "--table-name", "users",
        "--key", json.dumps({"user_id": {"S": uid}}),
        "--update-expression", "SET #pw = :h",
        "--expression-attribute-names", json.dumps({"#pw": "password"}),
        "--expression-attribute-values", json.dumps({":h": {"S": hashed}})
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✔ {uid} — password hash updated")
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
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║  ✅  NSCS-Gate is now running in HARDENED mode       ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  Patches applied:                                    ║"
echo "  ║    [app.py]   Cryptographic session secret           ║"
echo "  ║    [app.py]   SSRF blocklist on /webhooks/test       ║"
echo "  ║    [app.py]   /api/status — internal info removed    ║"
echo "  ║    [app.py]   IDOR ownership check on /drive/share   ║"
echo "  ║    [app.py]   SHA-256 password hashing               ║"
echo "  ║    [lambda]   No hardcoded credentials               ║"
echo "  ║    [lambda]   Debug mode off, errors sanitized       ║"
echo "  ║    [main.tf]  S3/IAM/SQS/SNS policies restricted     ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  ⚠  Run 'terraform apply' to apply infra changes     ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
