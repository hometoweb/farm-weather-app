import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- Constants ---
LAT, LON = -31.985688, 24.802269
WEATHERAPI_KEY = "95bd9405d0f24fd38b8125029251004"
WEATHERBIT_KEY = "f7a96d163c3e4c949cd127bc08fbbb79"

# --- API Requests ---
def get_weatherapi():
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={LAT},{LON}&days=10"
    res = requests.get(url)
    data = res.json()
    forecasts = []
    for day in data["forecast"]["forecastday"]:
        forecasts.append({
            "date": day["date"],
            "pop": float(day["day"].get("daily_chance_of_rain", 0)),
            "temp": float(day["day"].get("avgtemp_c", 0)),
            "wind": float(day["day"].get("maxwind_kph", 0)),
            "humidity": float(day["day"].get("avghumidity", 0)),
            "dew": float(day["hour"][12].get("dewpoint_c", 0)),
            "solar": None,
            "soil_moisture": None
        })
    return forecasts

def get_weatherbit():
    url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={LAT}&lon={LON}&key={WEATHERBIT_KEY}&days=10"
    res = requests.get(url)
    data = res.json()
    forecasts = []
    for day in data["data"]:
        forecasts.append({
            "date": day["valid_date"],
            "pop": float(day.get("pop", 0)),
            "temp": float(day.get("temp", 0)),
            "wind": float(day.get("wind_spd", 0)) * 3.6,
            "humidity": float(day.get("rh", 0)),
            "dew": float(day.get("dewpt", 0)),
            "solar": None,
            "soil_moisture": None
        })
    return forecasts

def get_openmeteo():
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}"
        f"&daily=precipitation_probability_mean,precipitation_sum,temperature_2m_max,windspeed_10m_max,dewpoint_2m_mean,"
        f"relative_humidity_2m_mean,shortwave_radiation_sum,soil_moisture_0_to_1cm_mean"
        f"&timezone=auto"
    )
    res = requests.get(url)
    data = res.json()

    # Check if 'daily' data exists in the response
    if "daily" not in data:
        # If not present, return an empty list or default values
        st.warning("Open-Meteo API did not return daily data. Using fallback values.")
        return []

    daily = data["daily"]
    keys = [
        "time", "precipitation_probability_mean", "precipitation_sum", "temperature_2m_max",
        "windspeed_10m_max", "dewpoint_2m_mean", "relative_humidity_2m_mean",
        "shortwave_radiation_sum", "soil_moisture_0_to_1cm_mean"
    ]

    # Initialize fallback values for missing data
    default_value = {
        "pop": 0,  # No rain
        "rain": 0,  # No rain (mm)
        "temp": 20,  # Default temperature in °C
        "wind": 5,  # Default wind speed in km/h
        "humidity": 50,  # Default relative humidity in %
        "dew": 10,  # Default dewpoint in °C
        "solar": 100,  # Default solar radiation (W/m²)
        "soil_moisture": 30  # Default soil moisture in percentage
    }

    forecasts = []
    for i in range(len(daily["time"])):
        date_str = daily["time"][i]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_name = date_obj.strftime("%A")  # Get weekday name (e.g., Monday)

        forecast = {
            "date": date_str,
            "weekday": weekday_name,
            "pop": daily.get("precipitation_probability_mean", [default_value["pop"]])[i],
            "rain": daily.get("precipitation_sum", [default_value["rain"]])[i],  # Rain amount (mm)
            "temp": daily.get("temperature_2m_max", [default_value["temp"]])[i],
            "wind": daily.get("windspeed_10m_max", [default_value["wind"]])[i],
            "humidity": daily.get("relative_humidity_2m_mean", [default_value["humidity"]])[i],
            "dew": daily.get("dewpoint_2m_mean", [default_value["dew"]])[i],
            "solar": daily.get("shortwave_radiation_sum", [default_value["solar"]])[i],
            "soil_moisture": daily.get("soil_moisture_0_to_1cm_mean", [default_value["soil_moisture"]])[i]
        }
        forecasts.append(forecast)

    return forecasts





# --- Drying Days Estimator ---
def estimate_drying_days(forecast):
    threshold = 3.0
    total = 0
    for i, day in enumerate(forecast):
        temp = day["temp"]
        wind = day["wind"]
        humidity = day["humidity"]
        solar = day["solar"] or 15
        soil = day["soil_moisture"] or 0.3

        drying_score = (
            (temp / 40) * 0.3 +
            (min(wind, 25) / 25) * 0.2 +
            ((1 - humidity / 100) * 0.2) +
            ((solar / 30) * 0.2) -
            ((soil / 0.6) * 0.2)
        )
        total += max(0, drying_score)
        if total >= threshold:
            return i + 1
    return None

# --- Average Forecasts ---
def average_forecasts(*sources):
    combined = {}
    for source in sources:
        for item in source:
            date = item["date"]
            if date not in combined:
                combined[date] = {key: [] for key in item}
            for key in item:
                combined[date][key].append(item[key] if item[key] is not None else 0)

    avg_forecast = []
    for date, values in sorted(combined.items()):
        entry = {"date": date}
        for key in values:
            if key != "date":
                entry[key] = round(sum(values[key]) / len(values[key]), 2)
        avg_forecast.append(entry)

    drying_days = estimate_drying_days(avg_forecast)
    for day in avg_forecast:
        day["dry_day"] = drying_days if drying_days else "N/A"

    return avg_forecast

# --- UI ---
st.set_page_config("Rain Forecast", layout="centered")
st.title("🌾 Lucerne Drying Forecast")
st.caption("📍 Graaff-Reinet, South Africa")

try:
    wapi = get_weatherapi()
    wbit = get_weatherbit()
    ometeo = get_openmeteo()
    avg = average_forecasts(wapi, wbit, ometeo)

    # --- Chart ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d["date"] for d in avg],
        y=[d["pop"] for d in avg],
        mode="lines+markers",
        name="Rain % (Avg)",
        line=dict(color="blue", width=3),
        hovertemplate="Date: %{x}<br>Rain: %{y}%<extra></extra>"
    ))

    fig.update_layout(
        title="Chance of Rain (%)",
        xaxis_title="Date",
        yaxis_title="Probability",
        xaxis_fixedrange=True,
        yaxis_fixedrange=True,
        dragmode=False,
        template="simple_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Forecast Table ---
    st.subheader("📊 Forecast Details")
    st.dataframe(
        {
            "Date": [d["date"] for d in avg],
            "Rain %": [d["pop"] for d in avg],
            "Temp (°C)": [d["temp"] for d in avg],
            "Wind (km/h)": [d["wind"] for d in avg],
            "Humidity %": [d["humidity"] for d in avg],
            "Dew (°C)": [d["dew"] for d in avg],
            "Solar (MJ/m²)": [d["solar"] for d in avg],
            "Soil Moisture": [d["soil_moisture"] for d in avg],
            "Est. Dry Day": [d["dry_day"] for d in avg]
        },
        use_container_width=True
    )

except Exception as e:
    st.error(f"Error loading data: {e}")
