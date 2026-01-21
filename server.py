import os
import json
import requests
from flask import Flask, render_template, request, redirect, send_from_directory

# This ensures PythonAnywhere knows exactly where your folders are
current_dir = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(current_dir, 'templates')
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, 
            template_folder=template_folder, 
            static_folder=static_folder)

# When loading your JSON, use the full path
def load_data():
    json_path = os.path.join(static_folder, 'vehicles.json')
    with open(json_path) as f:
        return json.load(f)

# ROUTE: Homepage / Search Results
@app.route('/')
def index():
    vehicles = load_data()
    return render_template('index.html', vehicles=vehicles)

# ROUTE: Dynamic Vehicle Detail Page
@app.route('/items/item_<int:car_id>.html')
def item_detail(car_id):
    vehicles = load_data()
    car = next((c for c in vehicles if c['id'] == car_id), None)
    if car:
        return render_template('item_details.html', car=car)
    return "Vehicle Not Found", 404

# ROUTE: Global Assets (CSS/Logo)
@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('static/assets', path)

# ROUTE: Vehicle-specific files (Images)
@app.route('/items/<path:path>')
def send_item_files(path):
    return send_from_directory('static/items', path)

# ROUTE: Stripe Mock
@app.route('/stripe_mock.html')
def stripe_mock():
    # 1. Get the item ID from the URL (e.g. ?item=1)
    item_id = request.args.get('item', type=int)
    
    # 2. Load data and find the specific car
    vehicles = load_data()
    car = next((c for c in vehicles if c['id'] == item_id), None)
    
    # 3. If car exists, render the template with the car data
    if car:
        return render_template('stripe_mock.html', car=car)
    
    # Fallback if no ID is provided
    return "Vehicle Not Found", 404

# ROUTE: API Handle Reserve
@app.route('/api/reserve', methods=['POST'])
def reserve():
    email = request.form.get('email')
    item_id = request.form.get('item_id')
    
    # 1. LOG TO LOCAL CSV (Your existing code)
    csv_path = os.path.join(static_folder, 'leads.csv')
    try:
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([item_id, email, datetime.now()])
    except Exception as e:
        print(f"CSV Error: {e}")

    # 2. SEND TO PARDOT (The new part)
    # Replace this URL with your actual Pardot Form Handler URL
    pardot_url = "http://go.trustap.com/l/1105011/2026-01-20/964py2" 
    
    try:
        # We send the data to Pardot using the same field names they expect
        payload = {
            'email': email,
            # If you mapped other fields in Pardot (like 'vehicle_interest'), add them here:
            # 'vehicle_interest': item_id 
        }
        # Send the POST request efficiently with a short timeout
        requests.post(pardot_url, data=payload, timeout=2)
        print(f"Sent {email} to Pardot")
        
    except Exception as e:
        # We catch errors so the user flow NEVER breaks even if Pardot is down
        print(f"Pardot Error: {e}")

    # 3. REDIRECT USER (Your existing code)
    return redirect(f'/items/item_{item_id}.html?reserved=true')

if __name__ == '__main__':
    # '0.0.0.0' tells Flask to accept connections from any device on your network
    app.run(host='0.0.0.0', port=8000, debug=True)