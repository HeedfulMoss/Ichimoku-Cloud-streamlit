import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

def Ichimoku_cloud_func(df):
    high_9 = df['High'].rolling(window= 9).max()
    low_9 = df['Low'].rolling(window= 9).min()
    df['tenkan_sen'] = (high_9 + low_9) /2

    high_26 = df['High'].rolling(window= 26).max()
    low_26 = df['Low'].rolling(window= 26).min()
    df['kijun_sen'] = (high_26 + low_26) /2

    return df

st.set_page_config(page_title='Ichimoku Cloud Homepage')
st.header('Please select a ticker')

st.sidebar.subheader('Ticker Selector')
ticker_list = pd.read_csv('SP500 Index.csv')
tickerSymbol = st.sidebar.selectbox('Stock ticker', ticker_list)
tickerData = yf.Ticker(tickerSymbol) 
tickerDf = tickerData.history(period='3mo')
tickerDf = Ichimoku_cloud_func(tickerDf)
# Ticker data
st.header('**Ticker data**')
st.write(tickerDf)