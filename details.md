# 🛡️ CyberRange — Detailed Architecture & Operations Guide

This document provides a comprehensive breakdown of the CyberRange cloud security environment, including installation, architecture, simulated services, and the intentional vulnerabilities designed for security training.

---

## 🚀 1. Installation & Setup

### Prerequisites
1. **Docker & Docker Compose**: To run the simulated AWS environment (LocalStack) and custom web applications.
2. **Terraform**: To provision the AWS resources into LocalStack as infrastructure-as-code.
3. **AWS CLI**: To interact with the simulated cloud resources.

### Deployment Steps
The environment must be initialized in two phases: standing up the containers, and then deploying the cloud resources.

```bash
# Phase 1: Container Orchestration
# This starts LocalStack, builds the custom web apps, and spins up monitoring.
docker compose up -d --build

# Wait ~15-30 seconds for LocalStack to fully initialize on port 4566.

# Phase 2: Cloud Infrastructure Deployment
# This uses Terraform to inject resources into the running LocalStack container.
terraform init
terraform apply -auto-approve
```

### Teardown & Reset
To completely destroy the environment and start fresh:

```bash
# Windows
.\scripts\reset.ps1

# Linux/macOS
bash scripts/reset.sh
```

---

## 🏗️ 2. Core Architecture

The environment operates across three distinct layers, all contained within your local machine.

### Layer 1: The Network (Docker)
All components run on a custom Docker bridge network named `cyberrange`. This allows containers to resolve each other by internal hostnames (e.g., the web app can reach `http://localstack:4566`).

### Layer 2: Simulated Cloud Infrastructure (LocalStack)
**LocalStack** (`localhost:4566`) is the heart of the environment. It intercepts standard AWS API calls and handles them locally, simulating a real AWS region. The environment utilizes 12 distinct AWS services.

### Layer 3: Application Attack Surface
Custom, intentionally vulnerable applications built to simulate common cloud footprints:
- **Vulnerable Web App** (`localhost:8080`): Represents a public-facing corporate application.
- **Fake Metadata Service** (`internal:80`): Simulates the internal EC2 Instance Metadata Service (IMDS).

### Layer 4: Monitoring Stack
- **Prometheus** (`localhost:9090`): Time-series metrics collection.
- **Grafana** (`localhost:3000`): Visualization dashboards.
- **Node Exporter**: Host-level resource metrics.

---

## ☁️ 3. Deployed Cloud Resources Breakdown

The `main.tf` Terraform configuration deploys approximately 40 discrete AWS resources. Below is the detailed breakdown by service.

### 3.1 S3 (Simple Storage Service)
Two buckets are deployed:
1. `cyber-range-bucket`: A secure, restricted-access bucket.
2. `sensitive-data-bucket`: An intentionally misconfigured bucket.

**Planted Data (Seed Files):**
The `sensitive-data-bucket` is seeded with realistic "leaked" corporate data:
- `backups/credentials.csv`: Plaintext user credentials.
- `config/config.json`: Application configuration containing API keys.
- `.env`: A leaked production environment file with database connection strings.
- `keys/deploy_key.pem`: A fake RSA private key for SSH/deployment.
- `exports/customer_pii.csv`: Simulated Personally Identifiable Information (SSNs, credit cards).
- `backups/db_dump_2026-03-01.sql`: A simulated PostgreSQL database dump.
- `infrastructure/terraform.tfstate`: A leaked Terraform state file containing infrastructure secrets.
- `docs/internal_memo.md`: An internal communication providing breadcrumbs for lateral movement.

### 3.2 DynamoDB
A NoSQL database table named `users` configured with `PAY_PER_REQUEST` billing. It is pre-seeded with 5 user records representing different organizational roles (Administrator, Developer, Analyst, Intern, Service Account), including plaintext passwords and API keys.

### 3.3 IAM (Identity and Access Management)
This is the core of the privilege escalation scenarios.

**Users:**
- `admin-user`: Full `*` administrative access.
- `dev-user`: Overprivileged access to core services (S3, DynamoDB, Lambda) and, critically, `sts:AssumeRole` permissions for the vulnerable role.
- `intern-user`: Has `s3:*` (allowing bucket enumeration) and dangerous permissions like `iam:CreateUser` and `secretsmanager:GetSecretValue`.

**Roles:**
- `vulnerable-role`: Contains a wildcard policy (`Action: *`, `Resource: *`) and a dangerously broad trust policy allowing any AWS principal to assume it.
- `cross-account-data-access`: A role simulating a "confused deputy" vulnerability, trusting `Principal: { AWS = "*" }`.

### 3.4 Serverless (Lambda & API Gateway)
- **Lambda (`vulnerable-api`)**: A Python 3.9 function representing an internal API.
- **API Gateway**: Exposes the Lambda function to the public without any authentication (`authorization = "NONE"`).

### 3.5 Secrets Management
- **AWS Secrets Manager**: Contains three targeted secrets:
  - `prod/database/credentials`: Database connection details.
  - `prod/api/keys`: Third-party API tokens (Stripe, GitHub, etc.).
  - `prod/iam/dev-user-keys`: Contains the `dev-user` AWS access keys.
- **SSM Parameter Store**: Holds configuration data like connection strings, feature flags, and internal SSH commands.

### 3.6 Messaging (SQS & SNS)
- **SQS**: `order-processing-queue` and an unmonitored dead-letter queue (DLq).
- **SNS**: `security-alerts` and `order-notifications` topics.

### 3.7 KMS & CloudWatch
- **KMS Key**: `alias/cyberrange-master-key` with a wildcard resource policy.
- **CloudWatch Log Groups**: Configured to capture logs from the Lambda function and the vulnerable web application.

---

## 🎯 4. Intentional Vulnerabilities Explained

The environment is designed to teach cloud security by demonstrating the impact of common misconfigurations and poor coding practices.

### 4.1 S3 Bucket Misconfiguration
**The Flaw**: The `sensitive-data-bucket` has a Bucket Policy with `Principal: "*"` and `Action: ["s3:GetObject", "s3:ListBucket"]`.
**The Impact**: Anyone with the AWS CLI, even unauthenticated users, can list and download highly sensitive corporate data (PII, `.env` files, DB dumps).

### 4.2 IAM Privilege Escalation Chain
**The Flaw**: A combination of overprivileged "low-level" accounts and loose trust policies.
**The Impact (Attack Path)**:
1. An attacker gains access to the `intern-user` credentials.
2. The `intern-user` enumerates S3 and finds the `internal_memo.md`, which hints that the `dev-user` credentials are in Secrets Manager.
3. The `intern-user` uses their overly permissive `secretsmanager:GetSecretValue` right to steal the `dev-user` keys.
4. The `dev-user` lacks explicit `*` admin rights but possesses `sts:AssumeRole` permissions targeting the `vulnerable-role`.
5. The attacker assumes the `vulnerable-role`, gaining full administrative control of the cloud environment.

### 4.3 Web App: SSRF to IAM Credential Theft (Capital One Style)
**The Flaw**: The custom Flask application (`vulnerable-app`) has a URL fetching feature (`/fetch`) that does not validate or restrict the target URL.
**The Impact**:
1. An attacker submits the URL `http://metadata-service/latest/meta-data/iam/security-credentials/vulnerable-role`.
2. The vulnerable web app, running *inside* the secure network boundary, fetches this URL from the fake IMDS service.
3. The IMDS service responds with the temporary AWS credentials (Access Key, Secret Key, Session Token) associated with that role.
4. The attacker extracts these credentials and uses them locally via the AWS CLI to impersonate the application's role and interact with other cloud services.

### 4.4 Web App: OS Command Injection
**The Flaw**: The `/healthcheck` endpoint passes user input (`target`) directly into a shell command: `subprocess.run(f"ping -c 1 {target}", shell=True)`.
**The Impact**: By appending shell metacharacters (e.g., `localhost; cat /etc/passwd`), an attacker can execute arbitrary operating system commands on the container hosting the web application.

### 4.5 Serverless: Hardcoded Secrets & Information Disclosure
**The Flaw**: The Python Lambda function contains hardcoded AWS keys and database passwords. Furthermore, it runs in "Debug" mode, returning full stack traces and environment variables to the user when an exception occurs.
**The Impact**: Attackers interacting with the unauthenticated API Gateway endpoint can intentionally trigger errors (e.g., by sending malformed payloads) to force the backend to dump its internal configuration and hardcoded secrets directly to the HTTP response.

### 4.6 Messaging: Open Queue Policies
**The Flaw**: Both the SQS queue and the SNS topic have resource policies granting `Principal: "*"` full publish and subscribe rights.
**The Impact**: An attacker can subscribe an external endpoint (like an attacker-controlled webhook) to the SNS topic to intercept internal security alerts, or inject malicious messages straight into the SQS order processing queue to manipulate backend workers.

---
**Disclaimer:** This is a localized, intentionally broken environment. Do not use these patterns in production.
