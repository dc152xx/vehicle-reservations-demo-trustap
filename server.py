import os
import json
import requests
import csv
import logging
import time
from datetime import datetime
import random
from flask import Flask, session, render_template, request, redirect, send_from_directory

# 1. SETUP LOGGING (Standard Python Logging)
# This ensures logs appear in your PythonAnywhere Error Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# 2. SETUP APP & FOLDERS
current_dir = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(current_dir, 'templates')
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

# CRITICAL: Secret key required for Session memory
app.secret_key = 'super_secret_nada_demo_key'

# --- NEW: ALLOW SESSIONS IN IFRAME ---
# These settings tell the browser to allow the cookie even when embedded on another site
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # Required if SameSite is None'

# HELPER: Load Vehicle Data
def load_data():
    json_path = os.path.join(static_folder, 'vehicles.json')
    with open(json_path) as f:
        return json.load(f)

# ROUTE 1: Homepage (Sets the Golden Car)
@app.route('/')
def index():
    vehicles = load_data()
    
    # 1. Get current time
    now = time.time()
    
    # 2. Check if we recently picked a winner (within last 5 seconds)
    last_gen_time = session.get('last_gen_time', 0)
    
    if (now - last_gen_time) < 5:
        # A. TOO SOON: Keep the existing winner
        winner_id = session.get('golden_car_id', 1)
        logger.info(f"♻️ DUPLICATE DETECTED: Keeping Golden Car #{winner_id} (Request within 5s)")
    else:
        # B. FRESH START: Pick a new winner
        winner_id = random.randint(1, 8)
        session['golden_car_id'] = winner_id
        session['last_gen_time'] = now
        logger.info(f"🎰 NEW SESSION START: The Golden Car is #{winner_id}")
    
    return render_template('index.html', vehicles=vehicles)

# ROUTE 2: Vehicle Detail Page (Checks for Golden Car)
@app.route('/items/item_<int:car_id>.html')
def item_detail(car_id):
    vehicles = load_data()
    car = next((c for c in vehicles if c['id'] == car_id), None)
    
    # A. Check if this car is the winner stored in the session
    is_winner = False
    if 'golden_car_id' in session:
        # Compare current ID with the one stored in session
        if session['golden_car_id'] == car_id:
            is_winner = True
            logger.info(f"🎉 WINNER FOUND! User is looking at Golden Car #{car_id}")
    
    if car:
        # Pass 'is_winner' to the template
        return render_template('item_details.html', car=car, is_winner=is_winner)
    
    return "Vehicle Not Found", 404

# ROUTE 3: Handle Reservation (Pardot + CSV)
@app.route('/api/reserve', methods=['POST'])
def reserve():
    email = request.form.get('email')
    item_id = request.form.get('item_id')
    
    # A. LOG TO LOCAL CSV
    try:
        csv_path = os.path.join(current_dir, 'leads.csv')
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([email, datetime.now()])
    except Exception as e:
        logger.error(f"CSV Error: {e}")

    # B. SEND TO PARDOT
    pardot_url = "http://go.trustap.com/l/1105011/2026-01-20/964py2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        requests.post(pardot_url, data={'email': email}, headers=headers, timeout=2)
        logger.info(f"Sent {email} to Pardot successfully.")
    except Exception as e:
        logger.error(f"Pardot Error: {e}")

    # C. REDIRECT USER
    return redirect(f'/items/item_{item_id}.html?reserved=true')

# --- SUPPORT ROUTES ---

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('static/assets', path)

@app.route('/items/<path:path>')
def send_item_files(path):
    return send_from_directory('static/items', path)

@app.route('/actions_mock.html')
def actions_mock():
    item_id = request.args.get('item', type=int)
    vehicles = load_data()
    car = next((c for c in vehicles if c['id'] == item_id), None)
    if car:
        return render_template('actions_mock.html', car=car)
    return "Vehicle Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)