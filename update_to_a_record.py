import requests

# Cloudflare API credentials
API_TOKEN = ""   #cloudflare api token
ZONE_ID = ""     #cloudflare zone ID
RECORD_NAME = "safeguardi.com"  # Replace with your domain name

def get_ec2_public_ip():
    # IMDSv2 for EC2 instance metadata
    token_url = "http://169.254.169.254/latest/api/token"
    headers = {"X-aws-ec2-metadata-token-ttl-seconds": "21600"}
    token_response = requests.put(token_url, headers=headers)
    token_response.raise_for_status()
    token = token_response.text

    metadata_url = "http://169.254.169.254/latest/meta-data/public-ipv4"
    metadata_headers = {"X-aws-ec2-metadata-token": token}
    ip_response = requests.get(metadata_url, headers=metadata_headers)
    ip_response.raise_for_status()
    return ip_response.text.strip()

def update_to_a_record(ip_address):
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    # Get the existing A or CNAME record
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records?name={RECORD_NAME}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch DNS records: {response.text}")
    
    records = response.json().get("result", [])
    if records:
        # Update the existing record
        record_id = records[0]["id"]
        a_record = {
            "type": "A",
            "name": RECORD_NAME,
            "content": ip_address,
            "ttl": 1,  # Auto TTL
            "proxied": True,
        }
        update_url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record_id}"
        update_response = requests.put(update_url, headers=headers, json=a_record)
        if update_response.status_code != 200:
            raise Exception(f"Failed to update A record: {update_response.text}")
        print(f"Successfully updated {RECORD_NAME} to A record with IP {ip_address}")
    else:
        raise Exception(f"No existing DNS record found for {RECORD_NAME}")

def set_ssl_encryption_mode():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    # Change SSL mode to 'full'
    ssl_url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings/ssl"
    payload = {
        "value": "full"  # Set encryption mode to 'full'
    }
    response = requests.patch(ssl_url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to update SSL mode: {response.text}")
    print("Successfully updated SSL mode to 'Full'")


if __name__ == "__main__":
    try:
        public_ip = get_ec2_public_ip()
        update_to_a_record(public_ip)
        set_ssl_encryption_mode()
    except Exception as e:
        print(f"Error: {e}")

