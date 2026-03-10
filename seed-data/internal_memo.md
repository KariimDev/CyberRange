# Internal Memo — Infrastructure Migration Notes

**Date:** 2026-02-20  
**From:** Platform Team  
**To:** All Developers  

## Action Items

1. **AWS Credentials Rotation**
   - The `dev-user` account now has `sts:AssumeRole` permissions for the `vulnerable-role`.
   - All new services should use the `vulnerable-role` for cross-service access.
   - Access keys for `dev-user` are stored in Secrets Manager under `prod/iam/dev-user-keys`.

2. **Secrets Migration**
   - We've migrated all production secrets to **AWS Secrets Manager**.
   - Database credentials: `prod/database/credentials`
   - API keys: `prod/api/keys`
   - Please stop using `.env` files and hardcoded keys!

3. **SSM Parameter Store**
   - Application config has moved to SSM Parameter Store under `/prod/` prefix.
   - Use `aws ssm get-parameters-by-path --path /prod/ --recursive` to list them.

4. **Security Reminder**
   - Do NOT store sensitive files in the `sensitive-data-bucket` — it has a public policy!
   - The `cyber-range-bucket` is the secure bucket for internal use only.

## Contacts
- IAM issues: admin@cyberrange.local (password: P@ssw0rd123!)
- Oncall: jenkins.cyberrange.local:8080
