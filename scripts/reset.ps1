# ============================================
# CyberRange — Full Reset Script (Windows)
# Tears down and re-deploys the entire lab
# ============================================

Write-Host "🔄 CyberRange — Resetting environment..." -ForegroundColor Cyan
Write-Host ""

# 1. Destroy Terraform state
Write-Host "🗑️  Destroying Terraform resources..." -ForegroundColor Yellow
terraform destroy -auto-approve 2>$null

# 2. Stop and remove containers
Write-Host "🐳 Stopping containers..." -ForegroundColor Yellow
docker compose down -v --remove-orphans

# 3. Clean local state
Write-Host "🧹 Cleaning local state..." -ForegroundColor Yellow
Remove-Item -Recurse -Force .terraform -ErrorAction SilentlyContinue
Remove-Item -Force terraform.tfstate -ErrorAction SilentlyContinue
Remove-Item -Force terraform.tfstate.backup -ErrorAction SilentlyContinue
Remove-Item -Force lambda\handler.zip -ErrorAction SilentlyContinue

# 4. Rebuild and start containers
Write-Host "🔨 Rebuilding and starting containers..." -ForegroundColor Yellow
docker compose up -d --build

Write-Host "⏳ Waiting for LocalStack to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 5. Re-deploy infrastructure
Write-Host "🏗️  Deploying infrastructure..." -ForegroundColor Yellow
terraform init
terraform apply -auto-approve

Write-Host ""
Write-Host "✅ CyberRange reset complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  LocalStack:      http://localhost:4566"
Write-Host "  Vulnerable App:  http://localhost:8080"
Write-Host "  Grafana:         http://localhost:3000 (admin/admin)"
Write-Host "  Prometheus:      http://localhost:9090"
Write-Host ""
Write-Host "Run the challenges: see challenges/README.md"
