import requests

# Cloudflare API credentials
API_TOKEN = ""     #cloudflare API token
ZONE_ID = ""       # cloudflare zone ID
RECORD_NAME = "safeguardi.com"  # Replace with your domain name
TARGET_CNAME = "safeguardi.com.s3-website.ap-south-1.amazonaws.com"  # Replace with your target CNAME (S3 bucket hosting URL)

def update_to_cname_record():
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
        cname_record = {
            "type": "CNAME",
            "name": RECORD_NAME,
            "content": TARGET_CNAME,
            "ttl": 1,  # Auto TTL
            "proxied": True,  # Enable Cloudflare proxy (orange cloud)
        }
        update_url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record_id}"
        update_response = requests.put(update_url, headers=headers, json=cname_record)
        if update_response.status_code != 200:
            raise Exception(f"Failed to update CNAME record: {update_response.text}")
        print(f"Successfully updated {RECORD_NAME} to CNAME record pointing to {TARGET_CNAME} with proxy enabled.")
    else:
        raise Exception(f"No existing DNS record found for {RECORD_NAME}")


def set_ssl_to_flexible():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    # Change SSL mode to 'Flexible'
    ssl_url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings/ssl"
    payload = {
        "value": "flexible"  # Set encryption mode to 'Flexible'
    }
    response = requests.patch(ssl_url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to update SSL mode: {response.text}")
    print("Successfully updated SSL mode to 'Flexible'.")


if __name__ == "__main__":
    try:
        update_to_cname_record()
        set_ssl_to_flexible()
    except Exception as e:
        print(f"Error: {e}")
