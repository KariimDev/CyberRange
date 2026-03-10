# =============================================================
#  CYBERRANGE — Intentionally Vulnerable Cloud Infrastructure
#  ⚠️  DO NOT deploy this to real AWS — training purposes only
# =============================================================


# ─────────────────────────────────────────────────
#  1. S3 BUCKETS
# ─────────────────────────────────────────────────

# Secure bucket (admin-only, holds flags)
resource "aws_s3_bucket" "lab_bucket" {
  bucket = "cyber-range-bucket"
}

# VULNERABILITY: Public bucket with sensitive data exposed
resource "aws_s3_bucket" "sensitive_public_bucket" {
  bucket = "sensitive-data-bucket"
}

resource "aws_s3_bucket_policy" "public_access" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadAccess"
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject", "s3:ListBucket"]
      Resource  = [
        aws_s3_bucket.sensitive_public_bucket.arn,
        "${aws_s3_bucket.sensitive_public_bucket.arn}/*"
      ]
    }]
  })
}



# ─────────────────────────────────────────────────
#  2. S3 SEED DATA — Upload files into buckets
# ─────────────────────────────────────────────────

# Files in the PUBLIC bucket (discoverable by anyone)
resource "aws_s3_object" "credentials_csv" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "backups/credentials.csv"
  source = "${path.module}/seed-data/credentials.csv"
  etag   = filemd5("${path.module}/seed-data/credentials.csv")
}

resource "aws_s3_object" "config_json" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "config/config.json"
  source = "${path.module}/seed-data/config.json"
  etag   = filemd5("${path.module}/seed-data/config.json")
}

resource "aws_s3_object" "env_file" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = ".env"
  source = "${path.module}/seed-data/.env"
  etag   = filemd5("${path.module}/seed-data/.env")
}

resource "aws_s3_object" "ssh_key" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "keys/deploy_key.pem"
  source = "${path.module}/seed-data/ssh_key.pem"
  etag   = filemd5("${path.module}/seed-data/ssh_key.pem")
}

resource "aws_s3_object" "pii_data" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "exports/customer_pii.csv"
  source = "${path.module}/seed-data/pii_records.csv"
  etag   = filemd5("${path.module}/seed-data/pii_records.csv")
}

resource "aws_s3_object" "db_backup" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "backups/db_dump_2026-03-01.sql"
  source = "${path.module}/seed-data/backup.sql"
  etag   = filemd5("${path.module}/seed-data/backup.sql")
}

resource "aws_s3_object" "tf_state_leaked" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "infrastructure/terraform.tfstate"
  source = "${path.module}/seed-data/terraform.tfstate.backup.json"
  etag   = filemd5("${path.module}/seed-data/terraform.tfstate.backup.json")
}

resource "aws_s3_object" "internal_memo" {
  bucket = aws_s3_bucket.sensitive_public_bucket.id
  key    = "docs/internal_memo.md"
  source = "${path.module}/seed-data/internal_memo.md"
  etag   = filemd5("${path.module}/seed-data/internal_memo.md")
}



# ─────────────────────────────────────────────────
#  3. DYNAMODB
# ─────────────────────────────────────────────────

resource "aws_dynamodb_table" "users" {
  name         = "users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }
}

# Seed user records
resource "aws_dynamodb_table_item" "user_admin" {
  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    user_id    = { S = "USR001" }
    username   = { S = "admin" }
    email      = { S = "admin@cyberrange.local" }
    role       = { S = "administrator" }
    password   = { S = "P@ssw0rd123!" }
    api_key    = { S = "sk-admin-abc123def456" }
    last_login = { S = "2026-03-09T10:30:00Z" }
  })
}

resource "aws_dynamodb_table_item" "user_jsmith" {
  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    user_id    = { S = "USR002" }
    username   = { S = "jsmith" }
    email      = { S = "john.smith@cyberrange.local" }
    role       = { S = "developer" }
    password   = { S = "Welcome1!" }
    api_key    = { S = "sk-dev-jsmith-789xyz" }
    last_login = { S = "2026-03-08T14:22:00Z" }
  })
}

resource "aws_dynamodb_table_item" "user_mjones" {
  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    user_id    = { S = "USR003" }
    username   = { S = "mjones" }
    email      = { S = "mary.jones@cyberrange.local" }
    role       = { S = "analyst" }
    password   = { S = "Summer2026!" }
    last_login = { S = "2026-03-07T09:15:00Z" }
  })
}

resource "aws_dynamodb_table_item" "user_dbrown" {
  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    user_id  = { S = "USR004" }
    username = { S = "dbrown" }
    email    = { S = "dave.brown@cyberrange.local" }
    role     = { S = "intern" }
    password = { S = "Qwerty789" }
    notes    = { S = "Temporary account — review permissions before renewal" }
  })
}

resource "aws_dynamodb_table_item" "user_svc" {
  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    user_id  = { S = "USR005" }
    username = { S = "service-account" }
    email    = { S = "svc@cyberrange.local" }
    role     = { S = "service" }
    api_key  = { S = "sk-svc-MASTER-key-00000" }
    notes    = { S = "Used by CI/CD pipeline — do not disable" }
  })
}


# ─────────────────────────────────────────────────
#  4. IAM — Vulnerable Roles, Users & Policies
# ─────────────────────────────────────────────────

# VULNERABILITY: Role with overly permissive policy (admin access to everything)
resource "aws_iam_role" "vulnerable_role" {
  name = "vulnerable-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
        AWS     = "*"
      }
    }]
  })
}

# VULNERABILITY: Wildcard policy — allows ALL actions on ALL resources
resource "aws_iam_role_policy" "overly_permissive" {
  name = "overly-permissive-policy"
  role = aws_iam_role.vulnerable_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

# VULNERABILITY: IAM user with inline admin credentials
resource "aws_iam_user" "admin_user" {
  name = "admin-user"
}

resource "aws_iam_user_policy" "admin_full_access" {
  name = "admin-full-access"
  user = aws_iam_user.admin_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

resource "aws_iam_access_key" "admin_key" {
  user = aws_iam_user.admin_user.name
}

# VULNERABILITY: Developer user with too many permissions + sts:AssumeRole
resource "aws_iam_user" "dev_user" {
  name = "dev-user"
}

resource "aws_iam_user_policy" "dev_overprivileged" {
  name = "dev-overprivileged"
  user = aws_iam_user.dev_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ServiceAccess"
        Effect   = "Allow"
        Action   = ["s3:*", "dynamodb:*", "lambda:*", "iam:*", "secretsmanager:*", "ssm:*"]
        Resource = "*"
      },
      {
        Sid      = "AssumeVulnerableRole"
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = aws_iam_role.vulnerable_role.arn
      }
    ]
  })
}

resource "aws_iam_access_key" "dev_key" {
  user = aws_iam_user.dev_user.name
}

# VULNERABILITY: Intern user who shouldn't have IAM permissions
resource "aws_iam_user" "intern_user" {
  name = "intern-user"
}

resource "aws_iam_user_policy" "intern_excessive" {
  name = "intern-excessive"
  user = aws_iam_user.intern_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3ReadAll"
        Effect   = "Allow"
        Action   = ["s3:*"]
        Resource = "*"
      },
      {
        Sid      = "DangerousIAM"
        Effect   = "Allow"
        Action   = ["iam:CreateUser", "iam:CreateAccessKey", "iam:AttachUserPolicy", "iam:ListUsers", "iam:ListRoles"]
        Resource = "*"
      },
      {
        Sid      = "SecretRead"
        Effect   = "Allow"
        Action   = ["secretsmanager:ListSecrets", "secretsmanager:GetSecretValue"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_access_key" "intern_key" {
  user = aws_iam_user.intern_user.name
}

# VULNERABILITY: Cross-account role with wildcard trust (confused deputy)
resource "aws_iam_role" "cross_account_role" {
  name = "cross-account-data-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { AWS = "*" }
    }]
  })
}

resource "aws_iam_role_policy" "cross_account_access" {
  name = "cross-account-full-access"
  role = aws_iam_role.cross_account_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:*", "dynamodb:*", "secretsmanager:*", "ssm:*"]
      Resource = "*"
    }]
  })
}


# ─────────────────────────────────────────────────
#  5. LAMBDA — Vulnerable Function
# ─────────────────────────────────────────────────

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/handler.py"
  output_path = "${path.module}/lambda/handler.zip"
}

resource "aws_lambda_function" "vulnerable_api" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "vulnerable-api"
  role             = aws_iam_role.vulnerable_role.arn
  handler          = "handler.handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      # VULNERABILITY: Secrets in environment variables (visible in console)
      DB_HOST     = "prod-db.cyberrange.local"
      DB_PASSWORD = "Pr0d_DB_S3cret!"
      API_KEY     = "sk-proj-abc123def456"
      DEBUG       = "true"
    }
  }
}


# ─────────────────────────────────────────────────
#  6. API GATEWAY — No Authentication
# ─────────────────────────────────────────────────

resource "aws_api_gateway_rest_api" "vulnerable_api" {
  name        = "vulnerable-api"
  description = "API with no authentication - cyber range target"
}

resource "aws_api_gateway_resource" "api_resource" {
  rest_api_id = aws_api_gateway_rest_api.vulnerable_api.id
  parent_id   = aws_api_gateway_rest_api.vulnerable_api.root_resource_id
  path_part   = "data"
}

resource "aws_api_gateway_method" "api_method" {
  rest_api_id   = aws_api_gateway_rest_api.vulnerable_api.id
  resource_id   = aws_api_gateway_resource.api_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.vulnerable_api.id
  resource_id             = aws_api_gateway_resource.api_resource.id
  http_method             = aws_api_gateway_method.api_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.vulnerable_api.invoke_arn
}

resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.vulnerable_api.id

  depends_on = [
    aws_api_gateway_integration.lambda_integration
  ]
}

resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.vulnerable_api.id
  stage_name    = "prod"
}


# ─────────────────────────────────────────────────
#  7. SECRETS MANAGER
# ─────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "db_credentials" {
  name = "prod/database/credentials"
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    host     = "prod-db.cyberrange.local"
    port     = 5432
    username = "db_admin"
    password = "Pr0d_DB_S3cret!"
    database = "customer_data"
  })
}

resource "aws_secretsmanager_secret" "api_keys" {
  name = "prod/api/keys"
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    stripe_secret  = "sk_live_abc123456789"
    sendgrid_key   = "SG.abcdefghijk"
    jwt_secret     = "my-super-secret-jwt-key-do-not-share"
    github_token   = "ghp_xxxxxxxxxxxxxxxxxxxx"
  })
}

# Store dev-user keys in Secrets Manager (breadcrumb for priv esc chain)
resource "aws_secretsmanager_secret" "dev_user_keys" {
  name = "prod/iam/dev-user-keys"
}

resource "aws_secretsmanager_secret_version" "dev_user_keys" {
  secret_id = aws_secretsmanager_secret.dev_user_keys.id
  secret_string = jsonencode({
    access_key_id     = aws_iam_access_key.dev_key.id
    secret_access_key = "test"
    username          = "dev-user"
    note              = "Dev user has sts:AssumeRole for vulnerable-role"
  })
}



# ─────────────────────────────────────────────────
#  8. SSM PARAMETER STORE
# ─────────────────────────────────────────────────

resource "aws_ssm_parameter" "stripe_key" {
  name  = "/prod/api/stripe-key"
  type  = "String"
  value = "sk_live_abc123456789"
}

resource "aws_ssm_parameter" "db_connection" {
  name  = "/prod/database/connection-string"
  type  = "String"
  value = "postgresql://db_admin:Pr0d_DB_S3cret!@prod-db.cyberrange.local:5432/customer_data"
}

resource "aws_ssm_parameter" "app_config" {
  name  = "/prod/app/config"
  type  = "String"
  value = jsonencode({
    debug             = true
    log_level         = "DEBUG"
    admin_email       = "admin@cyberrange.local"
    feature_flags     = { new_ui = true, beta_api = true }
    encryption_key_id = "alias/cyberrange-master-key"
  })
}

resource "aws_ssm_parameter" "ssh_tunnel" {
  name  = "/prod/infra/ssh-bastion"
  type  = "String"
  value = "ssh -i deploy_key.pem ubuntu@bastion.cyberrange.local -L 5432:prod-db.cyberrange.local:5432"
}


# ─────────────────────────────────────────────────
#  9. SQS — Open Message Queue
# ─────────────────────────────────────────────────

resource "aws_sqs_queue" "orders_queue" {
  name                       = "order-processing-queue"
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 30
}

# VULNERABILITY: Queue policy allows ANYONE to send/receive messages
resource "aws_sqs_queue_policy" "orders_public" {
  queue_url = aws_sqs_queue.orders_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicAccess"
      Effect    = "Allow"
      Principal = "*"
      Action    = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource  = aws_sqs_queue.orders_queue.arn
    }]
  })
}

# Dead letter queue (often forgotten and unmonitored)
resource "aws_sqs_queue" "orders_dlq" {
  name = "order-processing-dlq"
}


# ─────────────────────────────────────────────────
#  10. SNS — Open Notification Topic
# ─────────────────────────────────────────────────

resource "aws_sns_topic" "security_alerts" {
  name = "security-alerts"
}

# VULNERABILITY: Anyone can subscribe or publish to this topic
resource "aws_sns_topic_policy" "security_alerts_public" {
  arn = aws_sns_topic.security_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicAccess"
      Effect    = "Allow"
      Principal = "*"
      Action    = ["sns:Subscribe", "sns:Publish", "sns:GetTopicAttributes"]
      Resource  = aws_sns_topic.security_alerts.arn
    }]
  })
}

resource "aws_sns_topic" "order_notifications" {
  name = "order-notifications"
}




# ─────────────────────────────────────────────────
#  12. CLOUDWATCH — Log Groups
# ─────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/vulnerable-api"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/cyberrange/vulnerable-app"
  retention_in_days = 7
}


# ─────────────────────────────────────────────────
#  13. KMS — Overly Permissive Encryption Key
# ─────────────────────────────────────────────────

resource "aws_kms_key" "vulnerable_key" {
  description = "Encryption key with overly permissive policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowEveryone"
      Effect    = "Allow"
      Principal = "*"
      Action    = "kms:*"
      Resource  = "*"
    }]
  })
}

resource "aws_kms_alias" "vulnerable_key" {
  name          = "alias/cyberrange-master-key"
  target_key_id = aws_kms_key.vulnerable_key.key_id
}


# ─────────────────────────────────────────────────
#  14. OUTPUTS
# ─────────────────────────────────────────────────

output "api_endpoint" {
  value       = "http://localhost:4566/restapis/${aws_api_gateway_rest_api.vulnerable_api.id}/prod/_user_request_/data"
  description = "The vulnerable API endpoint (no auth required)"
}

output "public_bucket" {
  value       = "sensitive-data-bucket"
  description = "The publicly accessible S3 bucket with sensitive data"
}

output "secure_bucket" {
  value       = "cyber-range-bucket"
  description = "The secure bucket (admin-only, contains flags)"
}

output "admin_access_key" {
  value       = aws_iam_access_key.admin_key.id
  description = "Admin user access key"
}

output "dev_access_key" {
  value       = aws_iam_access_key.dev_key.id
  description = "Dev user access key"
}

output "intern_access_key" {
  value       = aws_iam_access_key.intern_key.id
  description = "Intern user access key (start here for Challenge 03)"
}

output "vulnerable_role_arn" {
  value       = aws_iam_role.vulnerable_role.arn
  description = "ARN of the overprivileged role (priv esc target)"
}

output "cross_account_role_arn" {
  value       = aws_iam_role.cross_account_role.arn
  description = "ARN of the confused deputy role"
}

output "sqs_queue_url" {
  value       = aws_sqs_queue.orders_queue.id
  description = "SQS queue URL (publicly accessible)"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.security_alerts.arn
  description = "SNS topic ARN (publicly subscribable)"
}

output "vulnerable_app_url" {
  value       = "http://localhost:8080"
  description = "The SSRF-vulnerable web application"
}