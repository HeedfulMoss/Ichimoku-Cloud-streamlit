import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title='Ichimoku Cloud Homepage')
st.header('Please select a ticker')

st.sidebar.subheader('Ticker Selector')
ticker_list = pd.read_csv('SP500 Index.csv')
tickerSymbol = st.sidebar.selectbox('Stock ticker', ticker_list)
tickerData = yf.Ticker(tickerSymbol) 
tickerDf = tickerData.history(period='3mo')
# Ticker data
st.header('**Ticker data**')
st.write(tickerDf)