import json
import os
import boto3

# ============================================
# VULNERABILITY: Hardcoded secrets in code
# A real developer mistake - credentials should
# NEVER be hardcoded in source code
# ============================================
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
DB_PASSWORD = "SuperSecret123!"
API_TOKEN = "sk-proj-abc123def456ghi789"

# Another vulnerability: debug mode left on in production
DEBUG_MODE = True

# BUG FIX: "localhost:4566" inside a Lambda sandbox refers to the sandbox container itself,
# not the LocalStack host. LocalStack injects LOCALSTACK_HOSTNAME into every Lambda
# execution environment pointing to the actual LocalStack service host.
# Fall back to "localstack" (Docker network alias) if the env var isn't set.
LOCALSTACK_HOST = os.environ.get("LOCALSTACK_HOSTNAME", "localstack")
LOCALSTACK_ENDPOINT = f"http://{LOCALSTACK_HOST}:4566"

def handler(event, context):
    """
    Vulnerable Lambda function that:
    1. Has hardcoded credentials (secret scanning target)
    2. Returns sensitive info in error messages (info disclosure)
    3. Doesn't validate input (injection risk)
    4. Logs sensitive data when debug is on
    """

    if DEBUG_MODE:
        # VULNERABILITY: Logging sensitive request data
        print(f"DEBUG: Full event received: {json.dumps(event)}")
        print(f"DEBUG: Using DB password: {DB_PASSWORD}")

    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action", "")
        user_id = body.get("user_id", "")

        # VULNERABILITY: No input validation
        if action == "get_user":
            dynamodb = boto3.client(
                "dynamodb",
                endpoint_url=LOCALSTACK_ENDPOINT,
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name="us-east-1"
            )
            response = dynamodb.get_item(
                TableName="users",
                Key={"user_id": {"S": user_id}}
            )
            return {
                "statusCode": 200,
                "body": json.dumps(response, default=str)
            }

        elif action == "list_files":
            s3 = boto3.client(
                "s3",
                endpoint_url=LOCALSTACK_ENDPOINT,
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name="us-east-1"
            )
            response = s3.list_objects_v2(Bucket="sensitive-data-bucket")
            return {
                "statusCode": 200,
                "body": json.dumps(response, default=str)
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Unknown action"})
            }

    except Exception as e:
        # VULNERABILITY: Leaking internal error details to the client
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "debug_info": {
                    "db_password": DB_PASSWORD,
                    "aws_key": AWS_ACCESS_KEY,
                    "environment": dict(os.environ)
                }
            }, default=str)
        }
