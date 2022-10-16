import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
# import plotly.express as px


def Ichimoku_cloud_func(df):
    high_9 = df['High'].rolling(window= 9).max()
    low_9 = df['Low'].rolling(window= 9).min()
    df['tenkan_sen'] = (high_9 + low_9) /2

    high_26 = df['High'].rolling(window= 26).max()
    low_26 = df['Low'].rolling(window= 26).min()
    df['kijun_sen'] = (high_26 + low_26) /2

    df['chikou_span'] = df['Close'].shift(-26)


    for i in range(26):
        line = pd.to_datetime(df.index[-1] + timedelta(minutes=60))
        new_row = pd.DataFrame(index=[line])
        df = pd.concat([df, pd.DataFrame(new_row)], ignore_index=False)

    # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2))
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)

    # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2))
    period52_high = df['High'].rolling(window=52).max()
    period52_low = df['Low'].rolling(window=52).min()
    df['senkou_span_b'] = ((period52_high + period52_low) / 2).shift(26)

    return df

def conversion_base_crossover(df):
    df.loc[:, ('crossover1')] = (df.kijun_sen < df.tenkan_sen) & (df.kijun_sen.shift(1) > df.tenkan_sen.shift(1))

    return df

st.set_page_config(page_title='Ichimoku Cloud Homepage')
st.header('Please select a ticker')

st.sidebar.subheader('Ichimoku Cloud plot checker')
ticker_list = pd.read_csv('SP500 Index.csv')
# tickerSymbol = st.sidebar.selectbox('Stock ticker', ticker_list)
ticker_options = st.sidebar.multiselect(
    'What are your favorite colors',
    ticker_list,
    ['AAPL']
)

tickerSymbol = ticker_options[0]

tickerData = yf.Ticker(tickerSymbol) 
tickerDf = tickerData.history(period='1y')
tickerDf = Ichimoku_cloud_func(tickerDf)

st.write(ticker_options[0])
st.write(type(ticker_options))
st.header('**Ticker data**')
st.write(tickerDf)


fig = go.Figure(data=[go.Candlestick(x=tickerDf.index,
                open=tickerDf['Open'],
                high=tickerDf['High'],
                low=tickerDf['Low'],
                close=tickerDf['Close'])])

fig.add_trace(go.Scatter(x=tickerDf.index, y=tickerDf['tenkan_sen'], mode="lines", line=go.scatter.Line(color="blue")))
fig.add_trace(go.Scatter(x=tickerDf.index, y=tickerDf['kijun_sen'], mode="lines", line=go.scatter.Line(color="orange")))
fig.add_trace(go.Scatter(x=tickerDf.index, y=tickerDf['chikou_span'], mode="lines", line=go.scatter.Line(color="white")))
fig.add_trace(go.Scatter(x=tickerDf.index, y=tickerDf['senkou_span_a'], mode="lines", line=go.scatter.Line(color="red")))
fig.add_trace(go.Scatter(x=tickerDf.index, y=tickerDf['senkou_span_b'], mode="lines", line=go.scatter.Line(color="green")))

# fig.show()


st.plotly_chart(fig)
