import os
import json
import requests
import csv
import logging
import time
from datetime import datetime
import random
from flask import Flask, session, render_template, request, redirect, send_from_directory

# 1. SETUP LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# 2. SETUP APP & FOLDERS
current_dir = os.path.dirname(os.path.abspath(__file__))
# Assumes 'templates' and 'static' are in the same folder as server.py
template_folder = os.path.join(current_dir, 'templates')
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

# --- CONFIGURATION ---

# A. FEATURE FLAG: Hidden Car Game
# Default is False. Set HIDDEN_CAR_GAME=True in PythonAnywhere variables to enable.
app.config['HIDDEN_CAR_GAME'] = os.environ.get('HIDDEN_CAR_GAME') == 'True'

# B. SESSION SECURITY
app.secret_key = 'super_secret_nada_demo_key'
app.config['SESSION_COOKIE_SAMESITE'] = 'None' # Allow sessions in iframe (Pardot)
app.config['SESSION_COOKIE_SECURE'] = True     # Required for SameSite=None

# HELPER: Load Vehicle Data
def load_data():
    json_path = os.path.join(static_folder, 'vehicles.json')
    with open(json_path) as f:
        return json.load(f)

# ROUTE 1: Homepage (Sets the Hidden Car)
@app.route('/')
def index():
    vehicles = load_data()
    
    # 1. Check if the game is active
    game_active = app.config['HIDDEN_CAR_GAME']

    # 2. ONLY Run Game Logic if Active
    if game_active:
        now = time.time()
        last_gen_time = session.get('last_gen_time', 0)
        
        # Debounce Logic (Prevent Ghost Winner on double-load)
        if (now - last_gen_time) < 5:
            winner_id = session.get('golden_car_id', 1)
        else:
            winner_id = random.randint(1, 8)
            session['golden_car_id'] = winner_id
            session['last_gen_time'] = now
            # logger.info(f"🎰 GAME ON: The Golden Car is #{winner_id}")
    else:
        # Clear session if game is off, just to be safe
        session.pop('golden_car_id', None)

    # Pass 'hidden_car_game' flag to template
    return render_template('index.html', vehicles=vehicles, hidden_car_game=game_active)

# ROUTE 2: Vehicle Detail Page (Checks for Hidden Car)
@app.route('/items/item_<int:car_id>.html')
def item_detail(car_id):
    vehicles = load_data()
    car = next((c for c in vehicles if c['id'] == car_id), None)
    
    game_active = app.config['HIDDEN_CAR_GAME']
    is_winner = False

    # Check Winner ONLY if game is active
    if game_active and 'golden_car_id' in session:
        # Compare current ID with the one stored in session
        if str(session['golden_car_id']) == str(car_id):
            is_winner = True
            logger.info(f"🎉 WINNER FOUND! User is looking at Golden Car #{car_id}")
    
    if car:
        return render_template('item_details.html', car=car, is_winner=is_winner, hidden_car_game=game_active)
    
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

    # B. SEND TO PARDOT (Optional/Background)
    pardot_url = "http://go.trustap.com/l/1105011/2026-01-20/964py2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        requests.post(pardot_url, data={'email': email}, headers=headers, timeout=2)
        logger.info(f"Sent {email} to Pardot successfully.")
    except Exception as e:
        logger.error(f"Pardot Error: {e}")

    # C. REDIRECT USER (Mark as reserved + pass email)
    return redirect(f'/items/item_{item_id}.html?reserved=true&email={email}')

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