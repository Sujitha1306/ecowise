# app.py
# Main Flask application file for the EcoWise Advisor.

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


# --- App Initialization ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
# This configuration correctly handles cross-origin requests with credentials.
CORS(app, supports_credentials=True, origins=["http://localhost:3000"]) 

app.config['SECRET_KEY'] = 'a-very-secret-and-hard-to-guess-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'ecowise.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Appliance, User

# --- Multi-Model Loading ---
print("--- Loading all available ML models and scalers ---")
models = {}
scalers = {}
model_dir = os.path.join(basedir, 'ml', 'saved_model')
if os.path.exists(model_dir):
    for filename in os.listdir(model_dir):
        try:
            # Create a standardized, lowercase key from the filename
            if filename.endswith("_model.h5"):
                appliance_key = filename.replace("_model.h5", "")
                models[appliance_key] = load_model(os.path.join(model_dir, filename))
                print(f"Loaded model for key: '{appliance_key}'")
            elif filename.endswith("_scaler.pkl"):
                appliance_key = filename.replace("_scaler.pkl", "")
                with open(os.path.join(model_dir, filename), 'rb') as f:
                    scalers[appliance_key] = pickle.load(f)
                print(f"Loaded scaler for key: '{appliance_key}'")
        except Exception as e:
            print(f"Error loading file {filename}: {e}")

# --- Appliance-Specific Forecasting Function ---
def get_appliance_forecast(appliance_type):
    appliance_key = appliance_type.lower().replace(' ', '_')
    model = models.get(appliance_key)
    scaler = scalers.get(appliance_key)

    if not model or not scaler:
        print(f"Error: Model or scaler not found for key '{appliance_key}'.")
        return None

    try:
        DATASET_PATH = os.path.join(basedir, 'data', 'power_consumption.csv')
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
@app.route('/')
def index(): return "Welcome to the EcoWise Advisor Backend!"

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(); username, password, location = data.get('username'), data.get('password'), data.get('location', 'Not Specified')
    if not username or not password: return jsonify({'error': 'Username and password are required'}), 400
    if User.query.filter_by(username=username).first(): return jsonify({'error': 'Username already exists'}), 400
    new_user = User(username=username, location=location); new_user.set_password(password)
    db.session.add(new_user); db.session.commit()
    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(); username, password = data.get('username'), data.get('password')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password): return jsonify({'error': 'Invalid username or password'}), 401
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
    appliances_list = Appliance.query.all()
    result = [{'id': a.id, 'brand': a.brand, 'model': a.model, 'type': a.appliance_type} for a in appliances_list]
    return jsonify(result)

# --- Protected User Endpoints ---
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    logged_in_user_id = session.get('user_id')
    if not logged_in_user_id or logged_in_user_id != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id)
    user_appliances = [{'id': a.id, 'brand': a.brand, 'model': a.model} for a in user.appliances]
    return jsonify({'id': user.id, 'username': user.username, 'location': user.location, 'appliances': user_appliances})

@app.route('/user/<int:user_id>/appliance', methods=['POST'])
def add_user_appliance(user_id):
    logged_in_user_id = session.get('user_id')
    if not logged_in_user_id or logged_in_user_id != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id); data = request.get_json(); appliance_id = data.get('appliance_id')
    if not appliance_id: return jsonify({'error': 'Missing appliance_id'}), 400
    appliance = Appliance.query.get_or_404(appliance_id)
    if appliance in user.appliances: return jsonify({'message': 'Appliance already in user profile'}), 200
    user.appliances.append(appliance); db.session.commit()
    return jsonify({'message': f'Appliance {appliance.model} added to user {user.username}'}), 201
    
@app.route('/user/<int:user_id>/appliance/<int:appliance_id>', methods=['DELETE', 'OPTIONS'])
def remove_user_appliance(user_id, appliance_id):
    if request.method == 'OPTIONS': return jsonify({'status': 'ok'}), 200
    logged_in_user_id = session.get('user_id')
    if not logged_in_user_id or logged_in_user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id)
    appliance = Appliance.query.get_or_404(appliance_id)
    if appliance in user.appliances:
        user.appliances.remove(appliance)
        db.session.commit()
        return jsonify({'message': 'Appliance removed successfully'}), 200
    else:
        return jsonify({'error': 'Appliance not found in user profile'}), 404

@app.route('/user/<int:user_id>/appliance/<int:appliance_id>/suggestion', methods=['GET'])
def get_suggestion(user_id, appliance_id):
    logged_in_user_id = session.get('user_id')
    if not logged_in_user_id or logged_in_user_id != user_id: return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id)
    appliance = Appliance.query.get_or_404(appliance_id)
    if appliance not in user.appliances: 
        return jsonify({'error': f'Appliance does not belong to user.'}), 400
    forecast = get_appliance_forecast(appliance.appliance_type)
    if not forecast:
        return jsonify({'error': f'Could not retrieve forecast for {appliance.appliance_type}.'}), 500
    suggestion_text = generate_suggestion(user, appliance, forecast)
    return jsonify({'user': user.username,'appliance': f"{appliance.brand} {appliance.model}",'suggestion': suggestion_text})

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'instance')):
        os.makedirs(os.path.join(basedir, 'instance'))
    app.run(debug=True)

