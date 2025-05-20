import yfinance as yf
import pandas as pd
import streamlit as st
import requests

def fetch_ticker_data(ticker_name):
    """
    Fetch historic data from Yahoo Finance using yfinance for the given ticker.
    Returns a DataFrame with columns: [time, open, high, low, close, volume].
    """
    try:
        # Example: fetch data for 2024 only (adjust as you like)
        df = yf.Ticker(ticker_name).history(start="2024-01-01", end="2024-12-31")[['Open','High','Low','Close','Volume']]

        # Reset index, rename columns, format time as YYYY-MM-DD
        df = df.reset_index()
        df.columns = ['time','open','high','low','close','volume']
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df['time'] = df['time'].dt.strftime('%Y-%m-%d')

        print(df.head())

        return df
    except requests.exceptions.JSONDecodeError as e:
        st.error(f"Error decoding JSON response from Yahoo Finance API: {str(e)}")
        # Return empty DataFrame with correct columns to prevent downstream errors
        return pd.DataFrame(columns=['time','open','high','low','close','volume'])
    except Exception as e:
        st.error(f"Error fetching data for {ticker_name}: {str(e)}")
        # Return empty DataFrame with correct columns to prevent downstream errors
        return pd.DataFrame(columns=['time','open','high','low','close','volume'])