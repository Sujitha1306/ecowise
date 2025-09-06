
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import os
import pickle

# --- Configuration ---
DATASET_PATH = os.path.join('..', 'data', 'power_consumption.csv')
MODEL_SAVE_DIR ='saved_model'
LOOK_BACK = 24

def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset) - look_back - 1):
        a = dataset[i:(i + look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

def train():
    print("--- Starting Multi-Model Training Process ---")

    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset not found at {DATASET_PATH}")
        return

    print("Loading synthetic dataset...")
    df = pd.read_csv(DATASET_PATH)
    
    appliance_types = df['Appliance'].dropna().unique()
    print(f"Found appliance types to train models for: {list(appliance_types)}")

    if not os.path.exists(MODEL_SAVE_DIR):
        os.makedirs(MODEL_SAVE_DIR)

    for appliance_type in appliance_types:
        print(f"\n--- Training model for: {appliance_type} ---")
        
        appliance_df = df[df['Appliance'] == appliance_type]
        power_data = appliance_df[['PowerConsumption']].values.astype('float32')

        if len(power_data) < LOOK_BACK + 2:
            print(f"Not enough data for {appliance_type} to create a model. Skipping.")
            continue

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(power_data)

        trainX, trainY = create_dataset(scaled_data, LOOK_BACK)
        
        if len(trainX) == 0:
            print(f"Could not create training samples for {appliance_type}. Skipping.")
            continue
            
        trainX = np.reshape(trainX, (trainX.shape[0], trainX.shape[1], 1))
        
        model = Sequential([ LSTM(50, input_shape=(LOOK_BACK, 1)), Dense(1) ])
        model.compile(loss='mean_squared_error', optimizer='adam')
        
        print(f"Training {appliance_type} model...")
        model.fit(trainX, trainY, epochs=10, batch_size=32, verbose=0)

        # --- THIS IS THE FIX ---
        # Create a standardized, lowercase key for filenames (e.g., 'ev_charger')
        appliance_key = appliance_type.lower().replace(' ', '_')
        model_name = f"{appliance_key}_model.h5"
        scaler_name = f"{appliance_key}_scaler.pkl"
        
        model_path = os.path.join(MODEL_SAVE_DIR, model_name)
        scaler_path = os.path.join(MODEL_SAVE_DIR, scaler_name)
        
        model.save(model_path)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
            
        print(f"Successfully saved model to: {model_path}")

    print("\n--- All Model Training Complete! ---")

if __name__ == '__main__':
    train()

