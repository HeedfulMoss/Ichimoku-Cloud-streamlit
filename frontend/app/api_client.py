import requests
import pandas as pd
import os
import json

# Get backend URL from environment variable or use default
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

def get_ticker_data(ticker_name, conversion_len=9, base_len=26, lagging_len=26, leading_span_b_len=52, cloud_shift=26):
    """
    Fetch ticker data and Ichimoku Cloud calculations from the backend API.
    
    Returns two dataframes: ticker_data and ichimoku_data
    """
    url = f"{BACKEND_URL}/api/tickers/{ticker_name}"
    params = {
        "conversion_len": conversion_len,
        "base_len": base_len,
        "lagging_len": lagging_len,
        "leading_span_b_len": leading_span_b_len,
        "cloud_shift": cloud_shift
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        # Convert JSON data to pandas DataFrames
        ticker_df = pd.DataFrame(data["ticker_data"])
        ichimoku_df = pd.DataFrame(data["ichimoku_data"])
        
        return ticker_df, ichimoku_df
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to backend: {e}")
        # Return empty DataFrames or raise an exception
        return pd.DataFrame(), pd.DataFrame()