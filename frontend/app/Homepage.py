import streamlit as st
from app.api_client import get_ticker_data
from app.charts import render_chart

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

# Fetch data and Ichimoku calculations from the backend
df, df_ichimoku = get_ticker_data(
    ticker_name,
    conversion_len=conversion_len_in,
    base_len=base_len_in,
    lagging_len=lagging_len_in,
    leading_span_b_len=leading_span_b_len_in,
    cloud_shift=cloud_shift_len_in
)

if not df.empty and not df_ichimoku.empty:
    # Render the chart
    render_chart(df, df_ichimoku, ticker_name)
else:
    st.error(f"Failed to fetch data for ticker: {ticker_name}")