"""
Fake EC2 Instance Metadata Service (IMDS v1) — CyberRange
Simulates the real AWS metadata endpoint at 169.254.169.254.
Accessible from the vulnerable-app container via SSRF.

Returns fake IAM role credentials that work with LocalStack.
"""

from flask import Flask, request, jsonify
import json
import datetime

app = Flask(__name__)

# ── IMDSv1 Endpoints ─────────────────────────────────

@app.route("/latest/meta-data/", defaults={"path": ""})
@app.route("/latest/meta-data/<path:path>")
def meta_data(path):
    routes = {
        "": "ami-id\nami-launch-index\nhostname\ninstance-id\ninstance-type\nlocal-ipv4\npublic-ipv4\niam/\nplacement/\nnetwork/",
        "ami-id": "ami-0abcdef1234567890",
        "ami-launch-index": "0",
        "hostname": "ip-10-0-1-42.ec2.internal",
        "instance-id": "i-0abc123def456ghi7",
        "instance-type": "t3.medium",
        "local-ipv4": "10.0.1.42",
        "public-ipv4": "54.123.45.67",
        "placement/availability-zone": "us-east-1a",
        "iam/": "info\nsecurity-credentials/",
        "iam/info": json.dumps({
            "Code": "Success",
            "InstanceProfileArn": "arn:aws:iam::000000000000:instance-profile/vulnerable-role",
            "InstanceProfileId": "AIPA0000000000EXAMPLE"
        }),
        "iam/security-credentials/": "vulnerable-role",
        "iam/security-credentials/vulnerable-role": json.dumps({
            "Code": "Success",
            "Type": "AWS-HMAC",
            "AccessKeyId": "ASIAIOSFODNN7STOLEN",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/STOLEN_KEY_HERE",
            "Token": "FwoGZXIvYXdzEBYaDHVzLWVhc3QtMSJHMEUCIQCxmVaGk7nE8a0ylSTO5JKxBQ7sNraBMYPm8iDE3ko0RgIgV7A3L9xj2DBkfOXP4bTz9RkEl3hobNYJz0KZXWG10qwqvAUI",
            "Expiration": "2027-12-31T23:59:59Z",
            "LastUpdated": datetime.datetime.utcnow().isoformat() + "Z"
        }),
        "network/interfaces/macs/": "02:42:ac:11:00:02/",
    }
    result = routes.get(path)
    if result is None:
        return "Not Found", 404
    return result, 200, {"Content-Type": "text/plain"}

# ── User Data endpoint ────────────────────────────────

@app.route("/latest/user-data")
def user_data():
    return """#!/bin/bash
# Bootstrap script for the web server
export DB_HOST=prod-db.cyberrange.local
export DB_PASSWORD=Pr0d_DB_S3cret!
export AWS_DEFAULT_REGION=us-east-1
# Pull config from SSM
aws ssm get-parameter --name /prod/app/config --with-decryption --query Parameter.Value --output text
""", 200, {"Content-Type": "text/plain"}

# ── Identity Document ─────────────────────────────────

@app.route("/latest/dynamic/instance-identity/document")
def identity_document():
    return jsonify({
        "accountId": "000000000000",
        "architecture": "x86_64",
        "availabilityZone": "us-east-1a",
        "imageId": "ami-0abcdef1234567890",
        "instanceId": "i-0abc123def456ghi7",
        "instanceType": "t3.medium",
        "privateIp": "10.0.1.42",
        "region": "us-east-1",
        "version": "2017-09-30"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
