from datetime import datetime, timedelta
import numpy as np

# --- Configuration ---
PEAK_RATE_PER_KWH = 10.0
OFF_PEAK_RATE_PER_KWH = 5.0

# Define typical run times (in hours) for different appliance types
APPLIANCE_CYCLE_LENGTHS = {
    'Dishwasher': 2,
    'Washing Machine': 2,
    'Oven': 1,
    'Air Conditioner': 8,
    'Water Heater': 3,
    'Refrigerator': 24,
    'TV': 4,
    'Microwave Oven': 1, # Added from your dataset
    'EV Charger': 6,     # Added from your dataset
    'Default': 1
}

def find_cheapest_window(forecast, window_size):
    """
    Finds the starting hour of the cheapest continuous window of time in the forecast.
    """
    if not forecast or len(forecast) < window_size:
        return 0

    window_sums = []
    for i in range(len(forecast) - window_size + 1):
        window = forecast[i : i + window_size]
        window_sums.append(sum(window))

    if not window_sums:
        return 0

    best_start_hour_numpy = np.argmin(window_sums)
    
    # --- THIS IS THE FINAL FIX ---
    # Convert the special NumPy integer into a standard Python integer
    # before returning it, which prevents the TypeError.
    return int(best_start_hour_numpy)

def generate_suggestion(user, appliance, forecast):
    """
    Analyzes an appliance-specific forecast to generate a personalized, time-window-based suggestion.
    """
    if not forecast:
        return "Could not generate a suggestion due to a forecast error."

    appliance_type = appliance.appliance_type
    cycle_length = APPLIANCE_CYCLE_LENGTHS.get(appliance_type, APPLIANCE_CYCLE_LENGTHS['Default'])

    best_hour_from_now = find_cheapest_window(forecast, cycle_length) + 1

    suggestion_time = datetime.now() + timedelta(hours=best_hour_from_now)
    formatted_time = suggestion_time.strftime("%I:%M %p")

    consumption_kwh = appliance.avg_power_consumption_kwh or 0.0
    cost_at_peak = consumption_kwh * PEAK_RATE_PER_KWH
    cost_at_off_peak = consumption_kwh * OFF_PEAK_RATE_PER_KWH
    savings = max(0, cost_at_peak - cost_at_off_peak)
    formatted_savings = f"{savings:.2f}"

    if cycle_length > 1:
        suggestion = (
            f"Hi {user.username}, your {appliance.brand} {appliance.model} runs for about {cycle_length} hours. "
            f"For the best energy savings, start its next cycle around {formatted_time}. "
            f"This simple change can save you ~₹{formatted_savings} on this run."
        )
    else:
        suggestion = (
            f"Hi {user.username}, for your {appliance.brand} {appliance.model}, "
            f"the cheapest time to use it in the next 24 hours is around {formatted_time}. "
            f"This can save you ~₹{formatted_savings} and helps balance the grid."
        )

    return suggestion

