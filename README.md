# 🛡️ CyberRange — Cloud Security Lab

A local cloud security training environment (Cyber Range) for practicing attack and defense scenarios on simulated AWS infrastructure.

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Terraform](https://developer.hashicorp.com/terraform/downloads)
- [AWS CLI](https://aws.amazon.com/cli/)

### Setup
```bash
# 1. Start all containers (builds vulnerable-app and metadata-service)
docker compose up -d --build

# 2. Deploy the cloud infrastructure
terraform init
terraform apply -auto-approve

# 3. Verify everything is running
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets
```

### Reset
```bash
# Windows
.\scripts\reset.ps1

# Linux/macOS
bash scripts/reset.sh
```

## 🏗️ Architecture

| Service | Port | Purpose |
|---------|------|---------|
| **LocalStack** | `4566` | Simulated AWS (S3, DynamoDB, IAM, STS, Lambda, API GW, Secrets Manager, SSM, SQS, SNS, CloudTrail, KMS) |
| **Vulnerable App** | `8080` | Web app with SSRF, command injection, and info disclosure |
| **Metadata Service** | internal | Fake EC2 IMDS v1 (accessible via SSRF from vulnerable-app) |
| **Prometheus** | `9090` | Metrics collection |
| **Grafana** | `3000` | Monitoring dashboards (login: `admin`/`admin`) |
| **Node Exporter** | `9100` | Host system metrics |

## ☁️ AWS Resources

| Resource | Type | Description |
|----------|------|-------------|
| `sensitive-data-bucket` | S3 Bucket | Public policy — contains credentials, PII, backups, leaked configs |
| `cyber-range-bucket` | S3 Bucket | Secure bucket (restricted access) |
| `cyberrange-cloudtrail-logs` | S3 Bucket | CloudTrail audit logs |
| `users` | DynamoDB Table | 5 seeded user records with plaintext passwords |
| `vulnerable-role` | IAM Role | Wildcard `*:*` policy, overly broad trust |
| `cross-account-data-access` | IAM Role | Confused deputy — trusts any principal |
| `admin-user` | IAM User | Full admin access |
| `dev-user` | IAM User | Overprivileged — can assume `vulnerable-role` |
| `intern-user` | IAM User | Excessive IAM permissions for their role |
| `vulnerable-api` | Lambda + API GW | Hardcoded secrets, no auth, info disclosure in errors |
| `prod/database/credentials` | Secrets Manager | Database credentials |
| `prod/api/keys` | Secrets Manager | API keys and tokens |
| `prod/iam/dev-user-keys` | Secrets Manager | Dev user's IAM keys |
| `/prod/*` | SSM Parameters | Connection strings, configs, SSH commands |
| `order-processing-queue` | SQS | Public read/write policy |
| `security-alerts` | SNS Topic | Public subscribe/publish |
| `cyberrange-master-key` | KMS Key | Wildcard key policy |
| `cyberrange-trail` | CloudTrail | Audit trail logging to S3 |

## 📊 Monitoring

1. Open Grafana: [http://localhost:3000](http://localhost:3000)
2. Add Prometheus data source: `http://prometheus:9090`
3. Create dashboards using metrics like `node_cpu_seconds_total`

## 📁 Project Structure

```
CyberRange/
├── docker-compose.yml       # Container definitions
├── prometheus.yml           # Monitoring configuration
├── main.tf                  # AWS resource definitions
├── provider.tf              # Terraform provider config
├── variables.tf             # Configuration variables
├── lambda/
│   └── handler.py           # Vulnerable Lambda function
├── vulnerable-app/
│   ├── app.py               # SSRF + CMDi web app
│   └── Dockerfile
├── metadata-service/
│   ├── server.py            # Fake EC2 IMDS v1
│   └── Dockerfile
├── seed-data/               # Data seeded into AWS resources
│   ├── credentials.csv      # User credentials
│   ├── config.json          # App config with secrets
│   ├── .env                 # Leaked environment variables
│   ├── ssh_key.pem          # Leaked SSH key
│   ├── pii_records.csv      # Customer PII data
│   ├── backup.sql           # Database dump
│   ├── terraform.tfstate.backup.json  # Leaked infra state
│   └── internal_memo.md     # Internal document with breadcrumbs
└── scripts/
    ├── reset.ps1            # Windows reset
    └── reset.sh             # Linux/macOS reset
```

## ⚠️ Disclaimer

This environment is **intentionally vulnerable**. It is designed for local training only.
**NEVER** deploy these resources to a real AWS account.
