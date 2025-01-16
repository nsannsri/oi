# Open Interest (OI) Application

## Overview
This repository contains the source code for a dynamic, scalable Open Interest (OI) application. The project is designed to provide real-time market insights during trading hours and static snapshots post-market hours, all while optimizing costs and maintaining security.

## Features
- **Dynamic Hosting**: Flask application hosted on AWS EC2 during market hours.
- **Static Hosting**: Post-market data snapshot hosted on AWS S3 as a static website.
- **DNS Automation**: Cloudflare dynamically switches DNS records between EC2 (live market) and S3 (post-market).
- **Caching with MongoDB**: Reduces API calls and avoids rate limits.
- **Automated EC2 Lifecycle Management**: AWS EventBridge schedules start/stop of the EC2 instance to save costs.
- **Security**: Cloudflare headers and S3 bucket policies ensure secure access.

---

## Prerequisites
1. **AWS Setup**:
   - AWS account with access to:
     - EC2
     - S3
     - EventBridge
     - IAM for creating access keys
   - An S3 bucket with static website hosting enabled.

2. **Cloudflare Setup**:
   - Cloudflare account with your domain configured.
   - API token with permissions to manage DNS records and SSL settings.

3. **Dhan Account Setup**:
   - A **DhanHQ** account with API access enabled.
   - API credentials (Client ID and Access Token) for accessing market data.

4. **MongoDB**:
   - A running MongoDB instance (local or cloud-hosted) with access for caching real-time data.

5. **Python**:
   - Python 3.8 or above installed.
   - Virtual environment setup (recommended).

6. **Dependencies**:
   - Install required Python packages using `requirements.txt`:
     ```bash
     pip install -r requirements.txt
     ```

---

## Setup Instructions

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-repo/oi-application.git
cd oi-application
```

### Step 2: Environment Variables
Store the following keys securely in an `.env` file:

```env
# AWS Configuration
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_REGION=your_aws_region
S3_BUCKET_NAME=your_s3_bucket_name

# Cloudflare Configuration
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
CLOUDFLARE_ZONE_ID=your_cloudflare_zone_id
DOMAIN_NAME=your_domain_name

# DhanHQ API Configuration
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token

# MongoDB Configuration
MONGO_URI=mongodb://your_mongo_uri
```

### Step 3: Configure AWS Services
1. **S3 Bucket**:
   - Enable static website hosting on your S3 bucket.
   - Add a bucket policy to allow Cloudflare traffic with the injected Referrer header.

2. **EventBridge Scheduler**:
   - Create two EventBridge rules:
     - **Start EC2 instance** before market hours.
     - **Stop EC2 instance** after market hours.

3. **IAM Permissions**:
   - Ensure the IAM role attached to your EC2 instance allows access to S3 and CloudWatch.

### Step 4: Deploy the Flask Application
1. Copy the repository contents to your EC2 instance.
2. Start the application using the provided `oi.service` file:
   ```bash
   sudo systemctl start oi.service
   sudo systemctl enable oi.service
   ```

### Step 5: Set Up Cron Jobs
Add the following cron jobs to the EC2 instance:
```bash
# Generate and upload index.html post-market hours
30 15 * * * /usr/bin/python3 /path/to/upload.py >> /var/log/s3_upload.log 2>&1

# Update DNS to CNAME (S3 bucket)
40 15 * * * /usr/bin/python3 /path/to/update_to_cname_record.py >> /var/log/update_to_cname.log 2>&1
```

### Step 6: Update API Keys in Scripts
- **upload.py**:
  Update the following variables in the script:
  ```python
  AWS_ACCESS_KEY = "your_aws_access_key"
  AWS_SECRET_KEY = "your_aws_secret_key"
  AWS_REGION = "your_aws_region"
  S3_BUCKET_NAME = "your_s3_bucket_name"
  MONGO_URI = "your_mongo_uri"
  ```

- **update_to_a_record.py**:
  Update the following variables in the script:
  ```python
  API_TOKEN = "your_cloudflare_api_token"
  ZONE_ID = "your_cloudflare_zone_id"
  RECORD_NAME = "your_domain_name"
  ```

- **update_to_cname_record.py**:
  Update the following variables in the script:
  ```python
  API_TOKEN = "your_cloudflare_api_token"
  ZONE_ID = "your_cloudflare_zone_id"
  RECORD_NAME = "your_domain_name"
  TARGET_CNAME = "your_s3_bucket_website_endpoint"
  ```

- **app.py**:
  Update the following variables for DhanHQ API:
  ```python
  DHAN_CLIENT_ID = "your_dhan_client_id"
  DHAN_ACCESS_TOKEN = "your_dhan_access_token"
  ```

---

## Project Structure
```plaintext
.
├── app.py                 # Flask application for live data
├── upload.py              # Generates and uploads static index.html
├── update_to_a_record.py  # Updates DNS to EC2 public IP
├── update_to_cname_record.py  # Updates DNS to S3 bucket CNAME
├── templates/             # Jinja2 templates for index.html
├── static/                # Static assets (if needed)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not committed to GitHub)
├── oi.service             # Systemd service file for Flask app
├── crontab.txt            # Example cron jobs for automation
└── README.md              # Project documentation
```

---

## Usage
1. **Live Market Hours**:
   - The EC2 instance runs the Flask app, serving real-time OI data.
   - MongoDB caches data to minimize API calls.

2. **Post-Market Hours**:
   - `upload.py` generates a static `index.html` using MongoDB data.
   - The file is uploaded to S3, and DNS switches to the static website.

---

## Security Best Practices
- **Environment Variables**: Store sensitive keys securely and never commit them to the repository.
- **Cloudflare**: Use Transform Rules to inject Referrer headers for S3 bucket access.
- **IAM Policies**: Restrict permissions to only the resources this project requires.

---

