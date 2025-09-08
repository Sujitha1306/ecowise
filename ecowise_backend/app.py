# app.py
from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import pandas as pd
from tensorflow.keras.models import load_model
import pickle
from sklearn.preprocessing import MinMaxScaler
from advisor_logic import generate_suggestion
import numpy as np
from datetime import date, timedelta # Import date and timedelta

# App initialization and ML model loading...
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"]) 
app.config['SECRET_KEY'] = 'a-very-secret-and-hard-to-guess-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'ecowise.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Appliance, User

print("--- Loading all available ML models and scalers ---")
models = {}
scalers = {}
model_dir = os.path.join(basedir, 'ml', 'saved_model')
if os.path.exists(model_dir):
    for filename in os.listdir(model_dir):
        try:
            if filename.endswith("_model.h5"):
                appliance_key = filename.replace("_model.h5", "")
                models[appliance_key] = load_model(os.path.join(model_dir, filename))
            elif filename.endswith("_scaler.pkl"):
                appliance_key = filename.replace("_scaler.pkl", "")
                with open(os.path.join(model_dir, filename), 'rb') as f:
                    scalers[appliance_key] = pickle.load(f)
        except Exception as e:
            print(f"Error loading file {filename}: {e}")

def get_appliance_forecast(appliance_type):
    appliance_key = appliance_type.lower().replace(' ', '_')
    model = models.get(appliance_key)
    scaler = scalers.get(appliance_key)
    if not model or not scaler:
        print(f"Error: Model or scaler not found for key '{appliance_key}'.")
        return None
    try:
        DATASET_PATH = os.path.join(basedir, 'data', 'power_consumption.csv') # Assuming this is the correct file name now
        df = pd.read_csv(DATASET_PATH)
        appliance_df = df[df['Appliance'] == appliance_type]
        if len(appliance_df) < 24: return None
        power_data = appliance_df[['PowerConsumption']].values.astype('float32')
        last_24_hours = power_data[-24:]
        last_24_hours_scaled = scaler.transform(last_24_hours)
        predictions_scaled = []
        current_batch = last_24_hours_scaled.reshape((1, 24, 1))
        for _ in range(24):
            current_pred = model.predict(current_batch, verbose=0)[0]
            predictions_scaled.append(current_pred)
            current_batch = np.append(current_batch[:,1:,:], [[current_pred]], axis=1)
        predictions = scaler.inverse_transform(predictions_scaled)
        return [float(p) for p in predictions]
    except Exception as e:
        print(f"An error occurred during prediction for {appliance_type}: {e}")
        return None

# --- API Endpoints ---
# (Authentication and other management endpoints are unchanged)
@app.route('/')
def index(): return "Welcome!"
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(); u, p, l = data.get('username'), data.get('password'), data.get('location', 'N/A')
    if not u or not p: return jsonify({'error': 'Username and password are required'}), 400
    if User.query.filter_by(username=u).first(): return jsonify({'error': 'Username already exists'}), 400
    new_user = User(username=u, location=l); new_user.set_password(p)
    db.session.add(new_user); db.session.commit()
    return jsonify({'message': 'User registered', 'user_id': new_user.id}), 201
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(); u, p = data.get('username'), data.get('password')
    user = User.query.filter_by(username=u).first()
    if user is None or not user.check_password(p): return jsonify({'error': 'Invalid credentials'}), 401
    session['user_id'] = user.id
    return jsonify({'message': 'Login successful', 'user_id': user.id, 'username': user.username})
@app.route('/logout', methods=['POST'])
def logout(): session.pop('user_id', None); return jsonify({'message': 'Logout successful'})
@app.route('/@me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'Not logged in'}), 401
    user = User.query.get(user_id)
    if not user: return jsonify({'error': 'User not found'}), 404
    return jsonify({'id': user.id, 'username': user.username, 'location': user.location})
@app.route('/appliances', methods=['GET'])
def get_appliances():
    appliances = Appliance.query.all()
    return jsonify([{'id': a.id, 'brand': a.brand, 'model': a.model, 'type': a.appliance_type} for a in appliances])
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if session.get('user_id') != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id)
    return jsonify({'id': user.id, 'username': user.username, 'appliances': [{'id': a.id, 'brand': a.brand, 'model': a.model} for a in user.appliances]})
@app.route('/user/<int:user_id>/appliance', methods=['POST'])
def add_user_appliance(user_id):
    if session.get('user_id') != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id); data = request.get_json(); appliance_id = data.get('appliance_id')
    if not appliance_id: return jsonify({'error': 'Missing appliance_id'}), 400
    appliance = Appliance.query.get_or_404(appliance_id)
    if appliance in user.appliances: return jsonify({'message': 'Already in profile'}), 200
    user.appliances.append(appliance); db.session.commit()
    return jsonify({'message': 'Appliance added'}), 201
@app.route('/user/<int:user_id>/appliance/<int:appliance_id>', methods=['DELETE', 'OPTIONS'])
def remove_user_appliance(user_id, appliance_id):
    if request.method == 'OPTIONS': return jsonify({'status': 'ok'}), 200
    if session.get('user_id') != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id); appliance = Appliance.query.get_or_404(appliance_id)
    if appliance in user.appliances:
        user.appliances.remove(appliance); db.session.commit()
        return jsonify({'message': 'Appliance removed'}), 200
    return jsonify({'error': 'Appliance not found'}), 404

# --- NEW DASHBOARD ENDPOINTS ---

@app.route('/user/<int:user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    if session.get('user_id') != user_id:
        return jsonify({'error': 'Forbidden'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Calculate consumption breakdown
    consumption_breakdown = []
    if user.appliances:
        for appliance in user.appliances:
            consumption_breakdown.append({
                'type': appliance.appliance_type,
                'consumption_kwh': appliance.avg_power_consumption_kwh
            })

    return jsonify({
        'username': user.username,
        'current_streak': user.current_streak,
        'total_savings': round(user.total_savings, 2),
        'consumption_breakdown': consumption_breakdown
    })

@app.route('/suggestion/accept', methods=['POST'])
def accept_suggestion():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    savings = data.get('savings', 0.0)

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Logic to update the streak
    if user.last_suggestion_date == yesterday:
        user.current_streak += 1 # Continue the streak
    elif user.last_suggestion_date != today:
        user.current_streak = 1 # Start a new streak
    # If they already accepted today, do nothing to the streak

    user.last_suggestion_date = today
    user.total_savings += savings
    db.session.commit()

    return jsonify({
        'message': 'Suggestion accepted!',
        'new_streak': user.current_streak,
        'new_total_savings': round(user.total_savings, 2)
    })

# --- UPDATED SUGGESTION ENDPOINT ---
# Now returns both the suggestion text and the savings amount.
@app.route('/user/<int:user_id>/appliance/<int:appliance_id>/suggestion', methods=['GET'])
def get_suggestion(user_id, appliance_id):
    if session.get('user_id') != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id); appliance = Appliance.query.get_or_404(appliance_id)
    if appliance not in user.appliances: return jsonify({'error': 'Appliance not found'}), 400
    forecast = get_appliance_forecast(appliance.appliance_type)
    if not forecast: return jsonify({'error': 'Could not retrieve forecast'}), 500
    
    result = generate_suggestion(user, appliance, forecast)
    
    return jsonify({
        'user': user.username, 
        'appliance': f"{appliance.brand} {appliance.model}",
        'suggestion': result['text'], 
        'savings': result['savings']
    })

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'instance')):
        os.makedirs(os.path.join(basedir, 'instance'))
    app.run(debug=True)

