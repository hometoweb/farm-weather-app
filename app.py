
import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --------- API FUNCTIONS --------- #

def get_weatherbit():
    try:
        api_key = st.secrets["f7a96d163c3e4c949cd127bc08fbbb79"]
        url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat=51.5074&lon=0.1278&days=7&key={api_key}"
        res = requests.get(url)
        data = res.json()
        forecasts = [{
            "source": "Weatherbit",
            "date": pd.to_datetime(day["valid_date"]).date(),
            "temp": day["temp"],
            "precip": day["precip"]
        } for day in data["data"]]
        return pd.DataFrame(forecasts)
    except Exception as e:
        st.warning(f"Weatherbit API skipped: {e}")
        return None

def get_open_meteo():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=0.1278&daily=temperature_2m_max,precipitation_sum&timezone=Europe%2FLondon"
        res = requests.get(url)
        data = res.json()
        forecasts = [{
            "source": "Open-Meteo",
            "date": pd.to_datetime(date_str).date(),
            "temp": temp,
            "precip": precip
        } for date_str, temp, precip in zip(data["daily"]["time"], data["daily"]["temperature_2m_max"], data["daily"]["precipitation_sum"])]
        return pd.DataFrame(forecasts)
    except Exception as e:
        st.warning(f"Open-Meteo API skipped: {e}")
        return None

def get_visual_crossing():
    try:
        api_key = st.secrets["95bd9405d0f24fd38b8125029251004"]
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/London/next7days?unitGroup=metric&key={api_key}&include=days"
        res = requests.get(url)
        data = res.json()
        forecasts = [{
            "source": "Visual Crossing",
            "date": pd.to_datetime(day["datetime"]).date(),
            "temp": day["temp"],
            "precip": day["precip"]
        } for day in data["days"]]
        return pd.DataFrame(forecasts)
    except Exception as e:
        st.warning(f"Visual Crossing API skipped: {e}")
        return None

# --------- MAIN APP --------- #

st.title("Farm Weather Forecast (7-Day View)")

dfs = [get_weatherbit(), get_open_meteo(), get_visual_crossing()]
dfs = [df for df in dfs if df is not None]

if not dfs:
    st.error("All API calls failed. Please try again later.")
    st.stop()

combined_df = pd.concat(dfs)
combined_df = combined_df.sort_values(["date", "source"])

# --------- PLOT GRAPH --------- #

st.subheader("Forecasted Rainfall (Next 7 Days)")

rain_chart_data = combined_df.groupby("date")["precip"].mean().reset_index()
rain_chart_data = rain_chart_data.set_index("date")
st.line_chart(rain_chart_data.rename(columns={"precip": "Rainfall (mm)"}))

# --------- SHOW TABLE --------- #

st.subheader("Detailed 7-Day Weather Forecast")
st.dataframe(combined_df)
