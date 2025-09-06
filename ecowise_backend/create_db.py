from app import app, db
from models import Appliance, User
import pandas as pd
import os

# --- Updated function to create appliances based on types found in the synthetic dataset ---
def create_appliances():
    """
    Reads the synthetic usage dataset to find all unique appliance types
    and creates a few sample models for each type in the database.
    This populates the KBIS with a diverse range of selectable appliances for the user.
    """
    print("Creating appliances from synthetic dataset types...")
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Read the NEW, larger dataset to discover all appliance types
    file_path = os.path.join(basedir, 'data', 'power_consumption.csv')
    
    if not os.path.exists(file_path):
        print(f"Dataset not found at {file_path}. Cannot create appliances.")
        return

    df = pd.read_csv(file_path)
    # Get a list of unique appliance types from the 'Appliance' column, filtering out 'None'
    appliance_types = df['Appliance'].dropna().unique()
    
    print(f"Found appliance types in dataset: {list(appliance_types)}")

    appliances_to_create = []

    # For each discovered type, we create two sample models for users to choose from
    for appliance_type in appliance_types:
        # Use the mean power consumption from the dataset as a baseline for our samples
        # This is a simple heuristic to create somewhat realistic data.
        mean_power = df[df['Appliance'] == appliance_type]['PowerConsumption'].mean()
        
        appliances_to_create.extend([
            Appliance(
                brand='BrandA', 
                model=f'EcoSmart {appliance_type}', 
                appliance_type=appliance_type, 
                avg_power_consumption_kwh=round(mean_power / 20000, 1), # Scaled heuristic
                avg_water_consumption_liters= 50 if 'Wash' in appliance_type or 'Dish' in appliance_type else None,
                has_delay_start=True, 
                has_eco_mode=True
            ),
            Appliance(
                brand='BrandB', 
                model=f'PowerSaver {appliance_type}', 
                appliance_type=appliance_type, 
                avg_power_consumption_kwh=round(mean_power / 25000, 1), # Scaled heuristic
                avg_water_consumption_liters= 60 if 'Wash' in appliance_type or 'Dish' in appliance_type else None,
                has_delay_start=True, 
                has_eco_mode=False
            )
        ])

    if not appliances_to_create:
        print("No appliances to create.")
        return

    db.session.bulk_save_objects(appliances_to_create)
    db.session.commit()
    print(f"{len(appliances_to_create)} total sample appliances created.")

# --- The rest of the file remains the same ---
def create_initial_user():
    print("Checking for initial user...")
    if User.query.filter_by(username='Priya').first() is None:
        print("Creating initial user 'Priya'...")
        user = User(username='Priya', location='Coimbatore')
        db.session.add(user)
        db.session.commit()
        print("User 'Priya' created.")
    else:
        print("User 'Priya' already exists.")

if __name__ == '__main__':
    with app.app_context():
        print("--- Database Setup Initializing ---")
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        create_appliances()
        create_initial_user()
        print("--- Database setup complete. ---")




