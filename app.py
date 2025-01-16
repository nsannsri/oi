from flask import Flask, render_template, jsonify, make_response
import pandas as pd
from dhanhq import dhanhq
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import os

# Initialize Flask application
app = Flask(__name__)

# MongoDB client setup
client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB URI if using a cloud-hosted MongoDB
db = client['market_data']
collection = db['option_chain_cache']

TESTING_MODE = False  # Set to True for testing, False for production


# Initialize Dhan API client
client_id = ''  # Replace with your client ID
access_token = ''  # Replace with your access token


dhan = dhanhq(client_id, access_token)

# Function to check if market is open
def is_market_open():
    # Define IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    
    # Get current time in UTC
    utc_now = datetime.utcnow()

    # Convert the UTC time to IST
    ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

    # Market open and close times in IST
    market_open_time = datetime.strptime("09:15:00", "%H:%M:%S").time()
    market_close_time = datetime.strptime("15:30:00", "%H:%M:%S").time()

    # Get the current time in IST (ignoring the date)
    current_time = ist_now.time()

    # Check if the market is open
    return market_open_time <= current_time <= market_close_time

# Function to update cache in MongoDB with retry mechanism
def update_cache():
    # Check if market is open
    if not TESTING_MODE and not is_market_open():
        logging.info("Market is closed. Serving data from MongoDB.")
        return

    max_retries = 3
    base_delay = 5  # seconds for exponential backoff

    for attempt in range(max_retries):
        try:
            # Define parameters for the API call
            under_security_id = 26009  # Replace with actual security ID for Bank Nifty
            under_exchange_segment = "NSE_FNO"  # Segment for Bank Nifty options NSE_FNO
            expiry_date = "2025-01-30"  # Example expiry date

            # Fetch data from Dhan API
            option_chain_data = dhan.option_chain(
                under_security_id=under_security_id,
                under_exchange_segment=under_exchange_segment,
                expiry=expiry_date
            )

            # Check if data was retrieved successfully
            if option_chain_data.get('status') == 'success':
                # Process and structure data
                nested_data = option_chain_data['data']['data']
                last_price = nested_data.get('last_price')
                atm_strike = round(last_price / 100) * 100  # Calculate ATM strike price

                # Extract ±5 strikes from ATM
                option_chain = nested_data['oc']
                strikes_to_display = [float(atm_strike + i * 100) for i in range(-5, 6)]

                rows = []
                for strike_price_str, options in option_chain.items():
                    strike_price = float(strike_price_str)
                    if strike_price in strikes_to_display:
                        # CE values
                        ce_open_interest = options['ce'].get('oi', 0) / 100000
                        ce_previous_open_interest = options['ce'].get('previous_oi', 0) / 100000
                        ce_volume = options['ce'].get('volume', 0)
                        ce_ask = options['ce'].get('top_ask_price', 0)
                        ce_bid = options['ce'].get('top_bid_price', 0)
                        ce_spread = ce_ask - ce_bid
                        ce_mid = (ce_ask + ce_bid) / 2 if (ce_ask + ce_bid) != 0 else 1
                        ce_sp = (ce_spread / ce_mid) * 100 if ce_mid != 0 else 0

                        # PE values
                        pe_open_interest = options['pe'].get('oi', 0) / 100000
                        pe_previous_open_interest = options['pe'].get('previous_oi', 0) / 100000
                        pe_volume = options['pe'].get('volume', 0)
                        pe_ask = options['pe'].get('top_ask_price', 0)
                        pe_bid = options['pe'].get('top_bid_price', 0)
                        pe_spread = pe_ask - pe_bid
                        pe_mid = (pe_ask + pe_bid) / 2 if (pe_ask + pe_bid) != 0 else 1
                        pe_sp = (pe_spread / pe_mid) * 100 if pe_mid != 0 else 0

                        # Construct row data
                        row = {
                            'STP': strike_price,
                            'CLTP': options['ce'].get('last_price', 0),
                            'CEOI': ce_open_interest,
                            'CE-CH-OI': ce_open_interest - ce_previous_open_interest,
                            'CE-IV': options['ce'].get('implied_volatility', 0),
                            'CE-Delta': options['ce']['greeks'].get('delta', 0),
                            'CE-Gamma': options['ce'].get('gamma', 0),
                            'CE-Sp': ce_sp,
                            'PLTP': options['pe'].get('last_price', 0),
                            'PEOI': pe_open_interest,
                            'PE-CH-OI': pe_open_interest - pe_previous_open_interest,
                            'PE-IV': options['pe'].get('implied_volatility', 0),
                            'PE-Delta': options['pe']['greeks'].get('delta', 0),
                            'PE-Gamma': options['pe'].get('gamma', 0),
                            'PE-Sp': pe_sp,
                            'PEOI - CEOI': pe_open_interest - ce_open_interest,
                            'Trending OI': (pe_open_interest - pe_previous_open_interest) - (ce_open_interest - ce_previous_open_interest),
                            'CE Volume': ce_volume,
                            'PE Volume': pe_volume,
                            'Total Volume Difference': pe_volume - ce_volume
                        }
                        rows.append(row)

                # Insert data into MongoDB with timestamp
                document = {
                    'timestamp': datetime.utcnow(),
                    'data': rows,
                    'atm_strike': atm_strike
                }
                collection.insert_one(document)
                logging.info(f"Cache updated in MongoDB at {datetime.utcnow()}")

                return  # Exit the function on successful fetch

            else:
                logging.error("Failed to retrieve data from Dhan API. Full Response: %s", option_chain_data)

        except Exception as e:
            logging.error("Exception occurred in update_cache attempt %d: %s", attempt + 1, e)

        # Exponential backoff
        delay = base_delay * (2 ** attempt)
        if attempt < max_retries - 1:
            logging.info("Retrying in %d seconds...", delay)
            time.sleep(delay)


# Route to serve the main page
@app.route('/')
def index():
    latest_data = collection.find_one(sort=[('timestamp', -1)])  # Retrieve the latest document from MongoDB
    if latest_data:
        # Generate a unique nonce for CSP
        nonce = os.urandom(16).hex()
        
        # Create response with CSP header containing the nonce
        response = make_response(
            render_template(
                'index.html', 
                data=latest_data['data'], 
                atm_strike=latest_data['atm_strike'], 
                timestamp=latest_data['timestamp'], 
                nonce=nonce  # Pass the nonce to the template
            )
        )
        
        # Set the CSP header to allow inline scripts and styles with the generated nonce
        response.headers['Content-Security-Policy'] = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'nonce-{nonce}';"
            f"base-uri 'self'; "
            f"object-src 'none'; "
            f"frame-ancestors 'self';"
        )
#        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    else:
        return "No data available in MongoDB", 500
# Route to provide data from MongoDB as JSON
@app.route('/api/data')
def get_data():
    latest_data = collection.find_one(sort=[('timestamp', -1)])
    if latest_data:
        response = make_response(jsonify({
            'data': latest_data['data'],
            'atm_strike': latest_data['atm_strike'],
            'timestamp': latest_data['timestamp']
        }))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
        return response
    else:
        return jsonify({'error': 'No data available'}), 500
# Initialize the scheduler to refresh cache every 1 minute
scheduler = BackgroundScheduler()
scheduler.add_job(update_cache, 'interval', minutes=1)
scheduler.start()

# Ensure scheduler is properly shut down on exit
import atexit
atexit.register(lambda: scheduler.shutdown())

@app.route('/api/initial', methods=['GET'])
def get_initial_data():
    """Provide dynamic ATM and STRIKE_INTERVAL values."""
    latest_data = collection.find_one(sort=[('timestamp', -1)])  # Fetch the latest data from MongoDB
    if latest_data:
        atm_strike = latest_data['atm_strike']  # Fetch ATM value
        strike_interval = 100  # Default interval, adjust if needed dynamically
        return jsonify({
            "atm": atm_strike,
            "strike_interval": strike_interval
        })
    else:
        return jsonify({"error": "No data available"}), 500



@app.after_request
def add_security_headers(response):
    # Content Security Policy (adjust or uncomment if needed)
    # response.headers['Content-Security-Policy'] = (
    #     "default-src 'self'; "
    #     "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    #     "style-src 'self' 'unsafe-inline'; "
    #     "img-src 'self' data:;"
    # )

    # Anti-clickjacking header
    # X-Content-Type-Options header

    # Remove the Server header

    return response


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    update_cache()  # Initial cache update
    app.run(port = 8000, debug=True)



