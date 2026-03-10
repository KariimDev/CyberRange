#!/usr/bin/env bash
# ============================================
# CyberRange — Full Reset Script (Linux/macOS)
# Tears down and re-deploys the entire lab
# ============================================

set -e

echo "🔄 CyberRange — Resetting environment..."
echo ""

# 1. Destroy Terraform state
echo "🗑️  Destroying Terraform resources..."
terraform destroy -auto-approve 2>/dev/null || true

# 2. Stop and remove containers
echo "🐳 Stopping containers..."
docker compose down -v --remove-orphans

# 3. Clean local state
echo "🧹 Cleaning local state..."
rm -rf .terraform/
rm -f terraform.tfstate terraform.tfstate.backup
rm -f lambda/handler.zip

# 4. Rebuild and start containers
echo "🔨 Rebuilding and starting containers..."
docker compose up -d --build

echo "⏳ Waiting for LocalStack to be ready..."
sleep 15

# 5. Re-deploy infrastructure
echo "🏗️  Deploying infrastructure..."
terraform init
terraform apply -auto-approve

echo ""
echo "✅ CyberRange reset complete!"
echo ""
echo "Services:"
echo "  LocalStack:      http://localhost:4566"
echo "  Vulnerable App:  http://localhost:8080"
echo "  Grafana:         http://localhost:3000 (admin/admin)"
echo "  Prometheus:      http://localhost:9090"
echo ""
echo "Run the challenges: see challenges/README.md"
