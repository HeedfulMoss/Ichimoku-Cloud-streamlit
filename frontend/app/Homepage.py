import streamlit as st
import os
import pandas as pd
import requests
from charts import render_chart

backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

# Minimal Streamlit homepage
st.set_page_config(page_title='Ichimoku Cloud Homepage')

st.sidebar.title("Parameters For Ichimoku Cloud Indicator")
ticker_name = st.sidebar.text_input("Enter Ticker Name Here:", "AAPL")

conversion_len_in = st.sidebar.number_input("Conversion Line Length", value=9)
base_len_in = st.sidebar.number_input("Base Line Length", value=26)
lagging_len_in = st.sidebar.number_input("Lagging Line Length", value=26)
leading_span_b_len_in = st.sidebar.number_input("Leading Span B Line Length", value=52)
cloud_shift_len_in = st.sidebar.number_input("Cloud Shift Length", value=26)

st.header(f'Ichimoku Cloud Chart: {ticker_name}')

try:
    resp_raw = requests.get(f"{backend_url}/data/{ticker_name}")
    resp_raw.raise_for_status()
    raw_payload = resp_raw.json()
    print("DEBUG raw_payload sample:")
    print(raw_payload["data"][:5])
    df = pd.DataFrame(raw_payload["data"])
except requests.RequestException as req_err:
    st.error(f"Error fetching raw data: {req_err}")
    st.stop()
except ValueError as json_err:
    st.error(f"Error parsing raw-data JSON: {json_err}")
    st.text(f"Response text: {resp_raw.text[:200]}…")
    st.stop()

# Fetch Ichimoku
try:
    ich_req = {
        "data": raw_payload["data"],
        "conversion_len": conversion_len_in,
        "base_len":       base_len_in,
        "lagging_len":    lagging_len_in,
        "leading_span_b_len": leading_span_b_len_in,
        "cloud_shift":        cloud_shift_len_in
    }

    resp_ichi = requests.post(f"{backend_url}/ichimoku", json=ich_req)
    resp_ichi.raise_for_status()
    ichi_payload = resp_ichi.json()
    # print("DEBUG ichi_payload sample:")
    # print(ichi_payload["data"][:5])
    df_ichimoku = pd.DataFrame(ichi_payload["data"])
except requests.RequestException as req_err:
    st.error(f"Error fetching Ichimoku data: {req_err}")
    st.stop()
except ValueError as json_err:
    st.error(f"Error parsing Ichimoku JSON: {json_err}")
    st.text(f"Response text: {resp_ichi.text[:200]}…")
    st.stop()

# Render the chart
render_chart(df, df_ichimoku, ticker_name)


