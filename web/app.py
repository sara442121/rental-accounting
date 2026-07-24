from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"customers": [], "tools": [], "rentals": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def dashboard():
    data = load_data()
    return render_template('index.html', 
                           customers=data.get('customers', []), 
                           tools=data.get('tools', []), 
                           rentals=data.get('rentals', []))

@app.route('/customers')
def customer_list():
    data = load_data()
    return render_template('customers.html', customers=data.get('customers', []))

@app.route('/tools')
def tools_list():
    data = load_data()
    return render_template('tools.html', tools=data.get('tools', []))

@app.route('/rentals')
def rentals_list():
    data = load_data()
    return render_template('rentals.html', rentals=data.get('rentals', []))

if __name__ == '__main__':
    app.run(debug=True)
