import boto3
from pymongo import MongoClient
from jinja2 import Template
from pytz import timezone
import datetime
import os

# MongoDB setup
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "market_data"
COLLECTION_NAME = "option_chain_cache"

# AWS S3 setup
S3_BUCKET_NAME = "safeguardi.com"    #s3 bucketname
AWS_REGION = ""            # s3 region 
AWS_ACCESS_KEY = ""        # IAM  Access key  
AWS_SECRET_KEY = ""        # IAM Secret access key


# Template for index.html
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Data Table</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f4f6f8;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            color: #333333;
        }

        .container {
            max-width: 90%;
            margin: 0 auto;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
        }

        h2 {
            text-align: center;
            font-weight: 600;
            font-size: 1.8em;
            color: #333333;
            margin-bottom: 5px;
            padding: 8px 0;
            border-bottom: 2px solid #e0e0e0;
            letter-spacing: 0.5px;
        }

        .subtitle {
            text-align: center;
            font-size: 1em;
            color: #888888;
            margin-top: -5px;
            margin-bottom: 20px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
            background-color: #ffffff;
            margin: 0 auto;
            border: 1px solid #ddd;
        }

        th, td {
            padding: 8px;
            text-align: center;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }

        th {
            background: linear-gradient(135deg, #0288d1, #01579b);
            color: #ffffff;
            font-weight: 600;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #004a99;
        }

        .footer {
            background: linear-gradient(135deg, #0288d1, #4db6ac);
            color: #000000;
            font-weight: bold;
            border-top: 2px solid #00796b;
        }

        .strike-price {
            background-color: #ffd966;
            font-weight: 600;
            color: #333333;
        }

        .atm-strike {
            background-color: #1b5e20;
            color: #000000; /* Changed text color to black */
            font-weight: bold;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
            padding: 8px;
            border: 1px solid #004d40;
        }

        tr:nth-child(even) {
            background-color: #f9fbfd;
        }

        tr:hover {
            background: linear-gradient(135deg, #e1f5fe, #f9fbfd);
            transform: scale(1.01);
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.2s ease;
        }

        .analysis-column {
            background-color: #e0f7fa;
            font-weight: bold;
        }

        .positive-diff {
            color: #4caf50;
        }

        .negative-diff {
            color: #e53935;
        }

        .footer .analysis-column {
            background-color: #b2dfdb;
            font-weight: bold;
        }

        .negative-oi {
            color: #e53935;
            font-weight: bold;
        }

        .green {
            color: green;
        }
        .red {
            color: red;
        }

        @media (max-width: 768px) {
            th, td {
                padding: 6px;
                font-size: 0.85em;
            }
        }
    </style>
</head>
<body>
<div class="container">
    <h2>Options Data Table</h2>
    <p>Data last fetched at: {{ timestamp }}</p>
    <p class="subtitle">Live updates of Call and Put options with market sentiment analysis</p>
    
    <table>
        <thead>
            <tr>
                <th colspan="6">Call (CE)</th>
                <th class="strike-price">Strike Price (STP)</th>
                <th colspan="6">Put (PE)</th>
                <th class="analysis-column">OI Diff</th>
                <th class="analysis-column">OI PCR</th>
                <th class="analysis-column">Trending OI</th>
            </tr>
            <tr>
                <th>OI (Lakhs)</th>
                <th>Change in OI (Lakhs)</th>
                <th>IV</th>
                <th>Delta</th>
                <th>CE-S</th>
                <th>LTP</th>
                <th class="strike-price">STP</th>
                <th>LTP</th>
                <th>Delta</th>
                <th>PE-S</th>
                <th>IV</th>
                <th>Change in OI (Lakhs)</th>
                <th>OI (Lakhs)</th>
                <th class="analysis-column">OI Diff</th>
                <th class="analysis-column">OI PCR</th>
                <th class="analysis-column">Trending OI</th>
            </tr>
        </thead>
        <tbody>
            {% for row in data %}
            <tr class="{{ 'atm-strike' if row.STP == atm_strike else '' }}">
                <td>{{ "%.2f"|format(row.CEOI) }}</td>
                <td>{{ "%.2f"|format(row['CE-CH-OI']) }}</td>
                <td>{{ "%.2f"|format(row['CE-IV']) }}</td>
                <td>{{ "%.2f"|format(row['CE-Delta']) }}</td>
                <td class="{{ 'green' if row['CE-Sp'] <= 1 else 'red' }}">{{ "%.2f"|format(row['CE-Sp']) }}</td>
                <td>{{ row.CLTP }}</td>
                <td class="strike-price">{{ row.STP }}</td>
                <td>{{ row.PLTP }}</td>
                <td>{{ "%.2f"|format(row['PE-Delta']) }}</td>
                <td class="{{ 'green' if row['PE-Sp'] <= 1 else 'red' }}">{{ "%.2f"|format(row['PE-Sp']) }}</td>
                <td>{{ "%.2f"|format(row['PE-IV']) }}</td>
                <td>{{ "%.2f"|format(row['PE-CH-OI']) }}</td>
                <td>{{ "%.2f"|format(row.PEOI) }}</td>
                <td class="analysis-column {{ 'positive-diff' if (row.PEOI - row.CEOI) > 0 else 'negative-diff' }}">{{ "%.2f"|format(row.PEOI - row.CEOI) }}</td>
                <td class="analysis-column">{{ "%.2f"|format(row.PEOI / row.CEOI) }}</td>
                <td class="analysis-column {{ 'positive-diff' if (row['PE-CH-OI'] - row['CE-CH-OI']) > 0 else 'negative-diff' }}">{{ "%.2f"|format(row['PE-CH-OI'] - row['CE-CH-OI']) }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr class="footer">
                <td>{{ "%.2f"|format(total_ce_oi) }}</td>
                <td>{{ "%.2f"|format(total_ce_change_oi) }}</td>
                <td colspan="1"></td>
                <td colspan="1"></td>
                <td colspan="1"></td>
                <td colspan="1"></td>
                <td class="strike-price">Totals</td>
                <td colspan="1"></td>
                <td colspan="1"></td>
                <td colspan="1"></td>
                <td colspan="1"></td>
                <td>{{ "%.2f"|format(total_pe_change_oi) }}</td>
                <td>{{ "%.2f"|format(total_pe_oi) }}</td>
                <td class="analysis-column {{ 'positive-diff' if total_oi_diff > 0 else 'negative-diff' }}">{{ "%.2f"|format(total_oi_diff) }}</td>
                <td class="analysis-column">{{ "%.2f"|format(total_oi_pcr) }}</td>
                <td class="analysis-column {{ 'positive-diff' if total_trending_oi > 0 else 'negative-diff' }}">{{ "%.2f"|format(total_trending_oi) }}</td>
            </tr>
        </tfoot>
    </table>
</div>
</body>
</html>
"""

def fetch_latest_data():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    latest_data = collection.find_one(sort=[("timestamp", -1)])
    client.close()
    if latest_data:
        return latest_data
    return None

def generate_html(data):
    total_ce_oi = sum(row['CEOI'] for row in data['data'])
    total_pe_oi = sum(row['PEOI'] for row in data['data'])
    total_ce_change_oi = sum(row['CE-CH-OI'] for row in data['data'])
    total_pe_change_oi = sum(row['PE-CH-OI'] for row in data['data'])
    total_oi_diff = total_pe_oi - total_ce_oi
    total_oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi != 0 else 0
    total_trending_oi = total_pe_change_oi - total_ce_change_oi

    utc_time = data["timestamp"]
    if isinstance(utc_time, str):
        utc_time = datetime.datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%fZ")

    ist_time = utc_time.replace(tzinfo=timezone("UTC")).astimezone(timezone("Asia/Kolkata"))
    formatted_time = ist_time.strftime("%Y-%m-%d %I:%M:%S %p")

    # Use atm_strike from the database
    atm_strike = data.get("atm_strike")
    print(f"ATM Strike Price: {atm_strike}")

    template = Template(HTML_TEMPLATE)
    return template.render(
        data=data["data"], 
        timestamp=formatted_time, 
        atm_strike=atm_strike,
        total_ce_oi=total_ce_oi,
        total_pe_oi=total_pe_oi,
        total_ce_change_oi=total_ce_change_oi,
        total_pe_change_oi=total_pe_change_oi,
        total_oi_diff=total_oi_diff,
        total_oi_pcr=total_oi_pcr,
        total_trending_oi=total_trending_oi
    )

def upload_to_s3(html_content, bucket_name, key):
    s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=html_content, ContentType="text/html")

def main():
    data = fetch_latest_data()
    if not data:
        print("No data available in MongoDB.")
        return

    html_content = generate_html(data)

    try:
        upload_to_s3(html_content, S3_BUCKET_NAME, "index.html")
        print(f"index.html successfully uploaded to S3 bucket {S3_BUCKET_NAME}.")
    except Exception as e:
        print(f"Failed to upload index.html to S3: {e}")

if __name__ == "__main__":
    main()

