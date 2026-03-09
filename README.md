# 🛡️ CyberRange — Cloud Security Lab

A local cloud security training environment (Cyber Range) for practicing attack and defense scenarios on simulated AWS infrastructure.

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Terraform](https://developer.hashicorp.com/terraform/downloads)
- [AWS CLI](https://aws.amazon.com/cli/)

### Setup
```bash
# 1. Start the containers
docker compose up -d

# 2. Deploy the cloud infrastructure
terraform init
terraform apply -auto-approve

# 3. Verify everything is running
aws --endpoint-url=http://localhost:4566 s3 ls
```

## 🏗️ Architecture

| Service | Port | Purpose |
|---------|------|---------|
| **LocalStack** | `4566` | Simulated AWS (S3, DynamoDB, IAM, Lambda, API Gateway) |
| **Prometheus** | `9090` | Metrics collection |
| **Grafana** | `3000` | Monitoring dashboards (login: `admin`/`admin`) |
| **Node Exporter** | `9100` | Host system metrics |

## ☁️ AWS Resources Created

| Resource | Type | Purpose |
|----------|------|---------|
| `cyber-range-bucket` | S3 Bucket | File storage target |
| `users` | DynamoDB Table | User data database |
| `vulnerable-role` | IAM Role | Privilege escalation practice |

## 📊 Monitoring

1. Open Grafana: [http://localhost:3000](http://localhost:3000)
2. Add Prometheus data source: `http://prometheus:9090`
3. Create dashboards using metrics like `node_cpu_seconds_total`

## 📁 Project Structure

```
CyberRange/
├── docker-compose.yml   # Container definitions
├── prometheus.yml       # Monitoring configuration
├── main.tf              # AWS resource definitions
├── provider.tf          # Terraform provider config
├── variables.tf         # Configuration variables
└── .gitignore           # Files excluded from git
```
