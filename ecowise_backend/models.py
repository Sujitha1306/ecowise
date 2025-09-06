# models.py
# Defines the database schema for the EcoWise Advisor.

from app import db
from werkzeug.security import generate_password_hash, check_password_hash # <--- 1. ADD THIS IMPORT

# --- Association Table for Many-to-Many Relationship ---
user_appliances = db.Table('user_appliances',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('appliance_id', db.Integer, db.ForeignKey('appliance.id'), primary_key=True)
)

class Appliance(db.Model):
    """
    Represents a high-end home appliance in our KBIS database.
    """
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(120), nullable=False, unique=True)
    appliance_type = db.Column(db.String(80), nullable=False)
    energy_star_rating = db.Column(db.Float, nullable=True)
    avg_power_consumption_kwh = db.Column(db.Float, nullable=False)
    avg_water_consumption_liters = db.Column(db.Float, nullable=True)
    has_eco_mode = db.Column(db.Boolean, default=False)
    has_delay_start = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Appliance {self.brand} {self.model}>'

class User(db.Model):
    """
    Represents a user of the EcoWise Advisor app.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    location = db.Column(db.String(120), nullable=False)
    
    # --- 2. ADD THE PASSWORD HASH FIELD ---
    password_hash = db.Column(db.String(256), nullable=True)

    wakeup_time_weekdays = db.Column(db.String(5), nullable=True)
    dishwasher_runs_per_week = db.Column(db.Integer, nullable=True)
    has_solar_panels = db.Column(db.Boolean, default=False)
    
    appliances = db.relationship('Appliance', secondary=user_appliances, lazy='subquery',
        backref=db.backref('users', lazy=True))

    # --- 3. ADD PASSWORD HELPER METHODS ---
    def set_password(self, password):
        """Creates a hashed password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks a password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'