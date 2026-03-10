# NSCS-Gate: Cloud Security Cyber Range

Welcome to **NSCS-Gate**, an intentionally vulnerable cloud environment designed for security training, penetration testing, and learning about cloud misconfigurations. 

Instead of focusing on traditional web application vulnerabilities (like cross-site scripting or SQL injection), this project is entirely dedicated to **Cloud Infrastructure Security**, specifically focusing on AWS (Amazon Web Services). 

It simulates a real-world corporate portal built on top of cloud services, but with catastrophic architectural flaws that allow you to steal credentials, download sensitive corporate data, and hijack cloud resources.

---

## 🏗️ How It Works (The Architecture)

This project runs a complete "fake" AWS cloud right on your local computer so you can hack it safely. 
It uses three main technologies:

1. **LocalStack (The Cloud Engine):** A tool that acts exactly like Amazon Web Services (AWS), but runs offline on your machine.
2. **Terraform (The Builder):** A tool that reads our configuration files and automatically builds the cloud infrastructure inside LocalStack (creating databases, storage buckets, and serverless functions).
3. **Docker (The Container):** Packages all of these tools and the vulnerable "NSCS-Gate" web application so they run seamlessly together on any computer.

### The Cloud Services Used
When you start the environment, it creates:
* **S3 (Simple Storage Service):** Cloud hard-drives used for storing files.
* **DynamoDB:** A NoSQL database storing user accounts.
* **Lambda:** "Serverless" backend code that runs on demand.
* **SQS & SNS:** Message queues and notification systems.
* **IAM (Identity and Access Management):** The permission system controlling who can do what.
* **Secrets Manager & SSM:** Secure vaults for storing passwords and configurations.
* **Metadata Service (IMDS):** A simulated internal server that provides temporary credentials to applications.

---

## 🚀 Getting Started (Installation & Setup)

You do not need an AWS account. Everything runs locally safely.

### Prerequisites
You need these three free tools installed on your computer:
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Must be running)
2. [Terraform](https://developer.hashicorp.com/terraform/install)
3. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

### Step 1: Start the Docker Infrastructure
Open your terminal (PowerShell or Command Prompt), navigate to the folder containing this project, and run:
```bash
docker compose up -d --build
```
*Wait about 30 seconds for all the services to start up.*

### Step 2: Build the Cloud Environment
Now, use Terraform to deploy the databases, buckets, and roles into the LocalStack cloud:
```bash
terraform init
terraform apply -auto-approve
```

### Step 3: Access the Application
Open your web browser and go to:
**http://localhost:8080**

You are now looking at the **NSCS-Gate** portal. Feel free to click around, create an account, upload files, and explore.

---

## 🎯 The Vulnerabilities (Exploitation & Remediation Guide)

This environment contains several critical cloud misconfigurations. Below is a guide explaining each flaw in simple terms, how a hacker would exploit it, and how a security engineer would fix it.

### 1. The SSRF Attack (Stealing Cloud Credentials)

**What is it?** 
Server-Side Request Forgery (SSRF) happens when an application is tricked into talking to an internal server that the outside internet shouldn't be able to reach. In the cloud, the most dangerous internal server is the **Instance Metadata Service (IMDS)**, which lives at the IP address `169.254.169.254` (or in our simulated case, `metadata-service`). This service hands out powerful, temporary access keys to the application.

**How to Exploit it:**
1. Log into the NSCS-Gate portal at `http://localhost:8080`.
2. Go to the **Webhooks** tab. This feature is designed to test external URLs (like `http://google.com`).
3. Instead of a normal website, ask the application to fetch the secret internal metadata endpoint by entering this URL:
   `http://metadata-service/latest/meta-data/iam/security-credentials/vulnerable-role`
4. Click "Test Connection".
5. The application will blindly reach out to the internal server, retrieve the raw AWS IAM Access Key, Secret Key, and Session Token, and display them on your screen. You have now stolen the server's identity.

**How to Fix it:**
* **Network Level:** Upgrade the cloud environment to require IMDSv2 (Version 2). IMDSv2 requires special encrypted headers that SSRF attacks cannot easily generate, blocking the attack completely.
* **Application Level:** Add strict validation to the Webhooks feature. Never allow the application to make outbound requests to internal IP addresses or domains.

---

### 2. Overprivileged Identity (Too Much Power)

**What is it?**
When the application runs, it uses an IAM Role (its identity card) to talk to the database and storage. The Principle of Least Privilege says an app should only have exactly the permissions it needs. Our app, however, has wildcard (`*`) permissions, meaning it is treated like an overall administrator.

**How to Exploit it:**
1. Using the Access Key and Secret Key you stole in Vulnerability #1, open your computer's terminal.
2. Configure your local AWS CLI to use the stolen keys:
   ```bash
   export AWS_ACCESS_KEY_ID="<STOLEN_ACCESS_KEY>"
   export AWS_SECRET_ACCESS_KEY="<STOLEN_SECRET_KEY>"
   export AWS_SESSION_TOKEN="<STOLEN_TOKEN>"
   ```
3. Because the role has too much power, you can ask the cloud to list every storage bucket it has:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 ls
   ```
4. You can also explore the Secrets vault:
   ```bash
   aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets
   ```

**How to Fix it:**
* **IAM Policy Enforcement:** Rewrite the Terraform code (`main.tf`). Look for the `aws_iam_policy` attached to the `vulnerable-role`. Change `Action = "*"` to specific, limited actions like `s3:PutObject` and restrict `Resource = "*"` to only the exact bucket the app needs.

---

### 3. S3 Bucket Misconfiguration (Public Data Exposure)

**What is it?**
Amazon S3 buckets are meant to store files securely. However, misconfigured S3 buckets are the #1 cause of major corporate data leaks. In our project, the `sensitive-data-bucket` has been given a reckless policy that allows anyone with *any* AWS account to read it. Furthermore, the administrators have placed highly sensitive backup files in it.

**How to Exploit it:**
1. Let's assume you found the name of the bucket (`sensitive-data-bucket`) via the overprivileged role above.
2. Use the AWS CLI to list everything inside the bucket:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 ls s3://sensitive-data-bucket/ --recursive
   ```
3. You will see sensitive files that were entirely hidden from the web portal, such as `configs/.env`, `backups/db-backup-2023.sql`, and `ssh/id_rsa`.
4. Download the `.env` file to your computer to steal the production passwords:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 cp s3://sensitive-data-bucket/configs/.env .
   cat .env
   ```

**How to Fix it:**
* **Bucket Policies:** Remove the `aws_s3_bucket_policy` in Terraform that grants `Principal: "*"` access.
* **Block Public Access:** Enforce "Block Public Access" at the account level on AWS so no bucket can ever accidentally be made public.

---

### 4. Direct Exposure of Cloud Vaults (Secrets Manager & SSM)

**What is it?**
AWS provides secure vaults (Secrets Manager and Systems Manager Parameter Store) to safely hold things like database passwords, so developers don't have to write them directly into the code. However, NSCS-Gate makes a critical mistake: it pulls the secrets from the vault, and then prints them directly to the user interface.

**How to Exploit it:**
1. Log into the NSCS-Gate portal.
2. Look at the **Dashboard** tab.
3. The page dynamically pulls the `CLOUD_CONFIG` variable from AWS Secrets Manager and prints `prod/database/credentials` right on the screen. The secure vault is doing its job, but the web application is carelessly leaking the vault's contents to regular users.

**How to Fix it:**
* **Code Review:** Modify `app.py`. The application should pull secrets into its background computer memory to use them (e.g., to connect to the database), but those secret variables should *never* be passed into the frontend HTML templates.

---

### 5. Inefficient & Insecure Database Authentication (DynamoDB Scan)

**What is it?**
DynamoDB is a massive, fast NoSQL database. The proper way to find a user is to perform a direct "Query" using an index (like searching their exact username). Instead, the NSCS-Gate login code performs a "Scan". A scan pulls *every single row* of the entire database into memory, reads them one by one, and checks if the username matches. 

**How to Exploit it:**
* **Data Exposure:** If an attacker finds a flaw in the python loop checking the scan, or if the system logs the output of the scan, the *entire* database of users and passwords is exposed.
* **Denial of Service (DoS):** Because a scan is so heavy, an attacker could write a script to rapidly attempt to log in 1,000 times a second. The database would exhaust all its compute resources pulling the whole table entirely into memory repeatedly, crashing the application and resulting in massive AWS cloud billing charges.

**How to Fix it:**
* **Refactoring:** Rewrite the `/login` route in `app.py`. Replace `dynamodb.scan()` with a specific `dynamodb.get_item()` or `dynamodb.query()` that only asks the cloud for the single row matching the exact `username` provided.

---

### 6. Serverless API Information Disclosure (Lambda)

**What is it?**
Serverless functions (AWS Lambda) spin up on demand to run small chunks of code. If poorly written, when they crash or encounter bad data, they can spit out their internal programming errors back to the user interface, revealing secret environment variables.

**How to Exploit it:**
1. Log into the NSCS-Gate portal.
2. Go to the **Serverless APIs** tab.
3. Select "Get User Details" and leave the "User ID" box completely blank. Click Invoke.
4. The Lambda function expects an ID. Because it receives nothing, the Python code inside the cloud function crashes.
5. Instead of gracefully returning a generic "Error", the Lambda function catches the exception and returns the *full stack trace* alongside its environment variables to help the "developer" debug.
6. Look closely at the error output. Because Lambda injects its own environment configurations silently, you will see highly sensitive internal AWS Keys and the hardcoded `DB_PASSWORD` printed right in the crash log.

**How to Fix it:**
* **Graceful Error Handling:** Developers must ensure that system exceptions (`try/except` blocks) log errors securely to an internal logging tool (like CloudWatch), and return a sanitized, polite message to the user: `{"error": "An expected error occurred."}`.
* **Secrets Management:** Never hardcode passwords (`DB_PASSWORD`) directly into Lambda environment variables. Have the Lambda function securely fetch them from Secrets Manager at runtime.

---

## 🧹 Cleanup and Teardown

When you are done experimenting and want to wipe everything clean, you can destroy the cloud resources and stop the Docker containers.

We have provided scripts that safely automate this process.

**If you are on Windows (PowerShell):**
```powershell
.\scripts\reset.ps1
```

**If you are on Mac/Linux (Bash):**
```bash
./scripts/reset.sh
```

This will run `terraform destroy` to delete the simulated cloud infrastructure and `docker compose down -v` to stop the environment entirely.
