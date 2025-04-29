
import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Weather Dashboard")

# -- User inputs (API keys, location, dates) --
weatherbit_key = st.text_input("f7a96d163c3e4c949cd127bc08fbbb79", type="password")
visualcrossing_key = st.text_input("95bd9405d0f24fd38b8125029251004", type="password")
lat = st.number_input("Latitude", value=40.7128)   # e.g. New York City
lon = st.number_input("Longitude", value=-74.0060)
start_date = st.date_input("Start Date", value=date.today())
end_date   = st.date_input("End Date", value=date.today() + timedelta(days=3))

# Ensure dates in ISO format strings
start_str = start_date.isoformat()
end_str = end_date.isoformat()

data_frames = []

# ---- Fetch from Weatherbit ----
if weatherbit_key:
    try:
        wb_url = "https://api.weatherbit.io/v2.0/forecast/daily"
        params = {"lat": lat, "lon": lon, "key": weatherbit_key, "days": (end_date - start_date).days + 1}
        wb_resp = requests.get(wb_url, params=params)
        # Handle HTTP errors explicitly
        if wb_resp.status_code == 429:
            st.warning("Weatherbit rate limit reached (429 Too Many Requests). Skipping Weatherbit data.")
        elif wb_resp.status_code != 200:
            st.warning(f"Weatherbit request failed with status code {wb_resp.status_code}.")
        else:
            # Parse JSON safely
            try:
                wb_data = wb_resp.json()
            except ValueError:
                st.warning("Weatherbit returned invalid JSON. Skipping Weatherbit data.")
                wb_data = None
            if wb_data and "data" in wb_data:
                df_wb = pd.DataFrame(wb_data["data"])
                # Convert date field and select relevant columns
                df_wb["date"] = pd.to_datetime(df_wb["datetime"]).dt.date
                # We use high_temp, low_temp, precip as example fields
                df_wb = df_wb[["date", "high_temp", "low_temp", "precip"]].copy()
                df_wb["source"] = "Weatherbit"
                data_frames.append(df_wb)
            else:
                st.warning("Weatherbit JSON missing expected fields. Skipping Weatherbit data.")
    except requests.exceptions.RequestException as e:
        st.warning(f"Weatherbit request encountered an error: {e}")

# ---- Fetch from Open-Meteo ----
try:
    om_url = "https://api.open-meteo.com/v1/forecast"
    om_params = {
        "latitude": lat,
        "longitude": lon,
        # Only valid daily fields; removed any invalid 'soil_moisture'
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "start_date": start_str,
        "end_date": end_str,
        "timezone": "UTC"
    }
    om_resp = requests.get(om_url, params=om_params)
    if om_resp.status_code != 200:
        st.warning(f"Open-Meteo request failed with status code {om_resp.status_code}.")
    else:
        try:
            om_data = om_resp.json()
        except ValueError:
            st.warning("Open-Meteo returned invalid JSON. Skipping Open-Meteo data.")
            om_data = None
        if om_data and "daily" in om_data:
            daily = om_data["daily"]
            # Check that expected keys exist
            if "time" in daily:
                df_om = pd.DataFrame({
                    "date": daily["time"],
                    "high_temp": daily.get("temperature_2m_max"),
                    "low_temp": daily.get("temperature_2m_min"),
                    "precip": daily.get("precipitation_sum")
                })
                df_om["date"] = pd.to_datetime(df_om["date"]).dt.date
                df_om["source"] = "Open-Meteo"
                data_frames.append(df_om)
            else:
                st.warning("Open-Meteo JSON missing 'time' field. Skipping Open-Meteo data.")
        else:
            st.warning("Open-Meteo JSON missing 'daily' data. Skipping Open-Meteo data.")
except requests.exceptions.RequestException as e:
    st.warning(f"Open-Meteo request encountered an error: {e}")

# ---- Fetch from Visual Crossing ----
if visualcrossing_key:
    try:
        vc_location = f"{lat},{lon}"
        vc_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{vc_location}/{start_str}/{end_str}"
        vc_params = {"unitGroup": "metric", "include": "days", "key": visualcrossing_key}
        vc_resp = requests.get(vc_url, params=vc_params)
        if vc_resp.status_code != 200:
            st.warning(f"Visual Crossing request failed with status code {vc_resp.status_code}.")
        else:
            try:
                vc_data = vc_resp.json()
            except ValueError:
                st.warning("Visual Crossing returned invalid JSON. Skipping Visual Crossing data.")
                vc_data = None
            if vc_data and "days" in vc_data:
                df_vc = pd.DataFrame(vc_data["days"])
                # Rename and select fields: datetime -> date, tempmax, tempmin, precip
                if "datetime" in df_vc.columns:
                    df_vc.rename(columns={"datetime": "date", "tempmax": "high_temp", "tempmin": "low_temp", "precip": "precip"}, inplace=True)
                    df_vc["date"] = pd.to_datetime(df_vc["date"]).dt.date
                    # Keep only these columns
                    cols = ["date", "high_temp", "low_temp", "precip"]
                    df_vc = df_vc[[col for col in cols if col in df_vc.columns]].copy()
                    df_vc["source"] = "Visual Crossing"
                    data_frames.append(df_vc)
                else:
                    st.warning("Visual Crossing JSON missing 'datetime' field in days. Skipping Visual Crossing data.")
            else:
                st.warning("Visual Crossing JSON missing 'days' data. Skipping Visual Crossing data.")
    except requests.exceptions.RequestException as e:
        st.warning(f"Visual Crossing request encountered an error: {e}")

# ---- Combine and display results ----
if data_frames:
    combined_df = pd.concat(data_frames, ignore_index=True)
    # Sort by date and then source for consistency
    combined_df.sort_values(by=["date", "source"], inplace=True)
    st.dataframe(combined_df)
else:
    st.write("No weather data available from any source.")

