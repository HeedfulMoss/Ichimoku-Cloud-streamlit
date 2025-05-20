import yfinance as yf
import pandas as pd

def fetch_ticker_data(ticker_name):
    """
    Fetch historic data from Yahoo Finance using yfinance for the given ticker.
    Returns a DataFrame with columns: [time, open, high, low, close, volume].
    """
    # Example: fetch data for 2024 only (adjust as you like)
    df = yf.Ticker(ticker_name).history(start="2024-01-01", end="2024-12-31")[['Open','High','Low','Close','Volume']]

    # Reset index, rename columns, format time as YYYY-MM-DD
    df = df.reset_index()
    df.columns = ['time','open','high','low','close','volume']
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df['time'] = df['time'].dt.strftime('%Y-%m-%d')

    print(df.head())

    return df
