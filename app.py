

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.title("10-Day Weather Forecast Comparison")

LAT = 51.5074
LON = -0.1278

# Add your API keys
WEATHERBIT_KEY = "f7a96d163c3e4c949cd127bc08fbbb79"
VISUAL_CROSSING_KEY = "95bd9405d0f24fd38b8125029251004"

def get_weatherbit():
    url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={LAT}&lon={LON}&key={WEATHERBIT_KEY}&days=10"
    res = requests.get(url)
    data = res.json()

    if "data" not in data:
        st.warning(f"Weatherbit API error: {data}")
        return []

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

def get_open_meteo():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,precipitation_probability_mean,windspeed_10m_max,relative_humidity_2m_mean,dew_point_2m_mean,soil_moisture_0_to_1cm_mean,shortwave_radiation_sum&timezone=auto"
    res = requests.get(url)
    data = res.json()

    if "daily" not in data:
        st.warning(f"Open-Meteo API error: {data}")
        return []

    daily = data["daily"]
    forecasts = []
    for i in range(len(daily["time"])):
        forecasts.append({
            "date": daily["time"][i],
            "pop": float(daily.get("precipitation_probability_mean", [0]*10)[i]),
            "temp": float(daily.get("temperature_2m_max", [0]*10)[i]),
            "wind": float(daily.get("windspeed_10m_max", [0]*10)[i]),
            "humidity": float(daily.get("relative_humidity_2m_mean", [0]*10)[i]),
            "dew": float(daily.get("dew_point_2m_mean", [0]*10)[i]),
            "solar": float(daily.get("shortwave_radiation_sum", [0]*10)[i]),
            "soil_moisture": float(daily.get("soil_moisture_0_to_1cm_mean", [0]*10)[i])
        })
    return forecasts

def get_visual_crossing():
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{LAT},{LON}?unitGroup=metric&key={VISUAL_CROSSING_KEY}&include=days"
    res = requests.get(url)
    data = res.json()

    if "days" not in data:
        st.warning(f"Visual Crossing API error: {data}")
        return []

    forecasts = []
    for day in data["days"][:10]:
        forecasts.append({
            "date": day["datetime"],
            "pop": float(day.get("precipprob", 0)),
            "temp": float(day.get("temp", 0)),
            "wind": float(day.get("windspeed", 0)),
            "humidity": float(day.get("humidity", 0)),
            "dew": float(day.get("dew", 0)),
            "solar": float(day.get("solarradiation", 0)),
            "soil_moisture": None
        })
    return forecasts

# Fetch data from APIs
weatherbit_data = get_weatherbit()
openmeteo_data = get_open_meteo()
visualcrossing_data = get_visual_crossing()

# Combine data into a single DataFrame
def to_df(data, source):
    df = pd.DataFrame(data)
    df["source"] = source
    return df

df = pd.concat([
    to_df(weatherbit_data, "Weatherbit"),
    to_df(openmeteo_data, "Open-Meteo"),
    to_df(visualcrossing_data, "Visual Crossing")
], ignore_index=True)

# Convert date to datetime object for sorting
df["date"] = pd.to_datetime(df["date"])

# Display the data
st.dataframe(df.sort_values(["date", "source"]))
