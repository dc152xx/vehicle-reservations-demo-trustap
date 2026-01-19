import os
import json
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
    return send_from_directory('static', 'stripe_mock.html')

# ROUTE: API Handle Reserve
@app.route('/api/reserve', methods=['POST'])
def handle_reserve():
    item_id = request.form.get('item_id')
    # Add your CSV logging here if needed
    return redirect(f'/items/item_{item_id}.html?reserved=true')

if __name__ == '__main__':
    # '0.0.0.0' tells Flask to accept connections from any device on your network
    app.run(host='0.0.0.0', port=8000, debug=True)