import streamlit as st
import os
import pandas as pd
import requests
from charts import render_chart

backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

# Minimal Streamlit homepage with AWS S3 integration
st.set_page_config(page_title='Ichimoku Cloud Homepage', layout="wide")

# Check AWS status first
@st.cache_data(ttl=300)  # Cache for 5 minutes
def check_aws_status():
    try:
        resp = requests.get(f"{backend_url}/aws/status", timeout=5)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"aws_available": False, "s3_connected": False}
    except:
        return {"aws_available": False, "s3_connected": False}

aws_status = check_aws_status()

st.sidebar.title("Parameters For Ichimoku Cloud Indicator")

# Ticker input
ticker_name = st.sidebar.text_input("Enter Ticker Name Here:", "AAPL")

# Ichimoku parameters
st.sidebar.subheader("Ichimoku Parameters")
conversion_len_in = st.sidebar.number_input("Conversion Line Length", value=9, min_value=1)
base_len_in = st.sidebar.number_input("Base Line Length", value=26, min_value=1)
lagging_len_in = st.sidebar.number_input("Lagging Line Length", value=26, min_value=1)
leading_span_b_len_in = st.sidebar.number_input("Leading Span B Line Length", value=52, min_value=1)
cloud_shift_len_in = st.sidebar.number_input("Cloud Shift Length", value=26, min_value=1)

# Data source options
st.sidebar.subheader("Data Source Options")

# Local CSV option
use_csv_backup = st.sidebar.checkbox(
    "Use Local CSV Backup", 
    value=False,
    help="Use local CSV backup data instead of Yahoo Finance (AAPL only)"
)

# AWS S3 options
if aws_status.get("s3_connected", False):
    st.sidebar.success(f"✅ AWS S3 Connected ({aws_status.get('bucket_name', 'unknown')})")
    
    use_s3_data = st.sidebar.checkbox(
        "Use AWS S3 Data",
        value=False,
        help="Try to fetch data from AWS S3 first"
    )
    
    use_s3_cache = st.sidebar.checkbox(
        "Use S3 Cache",
        value=True,
        help="Use cached data from S3 if available (faster, avoids API limits)"
    )
elif aws_status.get("aws_available", False):
    st.sidebar.warning("⚠️ AWS available but S3 not configured")
    use_s3_data = False
    use_s3_cache = False
else:
    st.sidebar.error("❌ AWS S3 not available")
    use_s3_data = False
    use_s3_cache = False

# Show warnings
if use_csv_backup and ticker_name.upper() != "AAPL":
    st.sidebar.warning("⚠️ Local CSV backup is only available for AAPL ticker")

if use_s3_data and not aws_status.get("s3_connected", False):
    st.sidebar.warning("⚠️ S3 options will be ignored (not connected)")

# Main content
st.header(f'Ichimoku Cloud Chart: {ticker_name}')

# Show data source priority info
with st.expander("ℹ️ Data Source Priority", expanded=False):
    st.write("""
    The application will try data sources in this order:
    1. **S3 Cache** (if enabled) - Fastest, uses cached Yahoo Finance data
    2. **S3 CSV Files** (if enabled) - Static CSV files uploaded to S3  
    3. **Local CSV Backup** (if enabled) - Only available for AAPL
    4. **Yahoo Finance API** - Live data with optional S3 caching
    """)

# Fetch raw data
try:
    # Build request parameters
    params = {}
    if use_csv_backup:
        params["use_csv"] = "true"
    if use_s3_data and aws_status.get("s3_connected", False):
        params["use_s3"] = "true"
    if use_s3_cache and aws_status.get("s3_connected", False):
        params["use_cache"] = "true"
    
    # Make request
    with st.spinner(f"Fetching data for {ticker_name}..."):
        resp_raw = requests.get(f"{backend_url}/data/{ticker_name}", params=params, timeout=30)
        resp_raw.raise_for_status()
        raw_payload = resp_raw.json()
    
    # Show data source info
    data_source_info = {
        's3_cache': '🌩️ AWS S3 Cache',
        's3_csv': '📁 AWS S3 CSV', 
        'local_csv': '💾 Local CSV',
        'yahoo_finance': '🌐 Yahoo Finance'
    }
    
    source_display = data_source_info.get(raw_payload.get('source'), raw_payload.get('source', 'Unknown'))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data Source", source_display)
    with col2:
        st.metric("Ticker", raw_payload.get('ticker', ticker_name))
    with col3:
        st.metric("Data Points", raw_payload.get('count', len(raw_payload.get('data', []))))
    
    df = pd.DataFrame(raw_payload["data"])
    
except requests.RequestException as req_err:
    st.error(f"Error fetching raw data: {req_err}")
    if hasattr(req_err, 'response') and req_err.response is not None:
        try:
            error_detail = req_err.response.json().get('detail', 'Unknown error')
            st.error(f"Server error: {error_detail}")
        except:
            st.error(f"HTTP {req_err.response.status_code} error")
    st.stop()
except ValueError as json_err:
    st.error(f"Error parsing raw-data JSON: {json_err}")
    if 'resp_raw' in locals():
        st.text(f"Response text: {resp_raw.text[:200]}…")
    st.stop()

# Fetch Ichimoku calculations
try:
    ich_req = {
        "data": raw_payload["data"],
        "conversion_len": conversion_len_in,
        "base_len": base_len_in,
        "lagging_len": lagging_len_in,
        "leading_span_b_len": leading_span_b_len_in,
        "cloud_shift": cloud_shift_len_in
    }

    with st.spinner("Calculating Ichimoku indicators..."):
        resp_ichi = requests.post(f"{backend_url}/ichimoku", json=ich_req, timeout=30)
        resp_ichi.raise_for_status()
        ichi_payload = resp_ichi.json()
    
    # Show calculation info
    st.success(f"✅ Ichimoku calculation complete ({ichi_payload.get('count', 0)} data points)")
    
    df_ichimoku = pd.DataFrame(ichi_payload["data"])
    
except requests.RequestException as req_err:
    st.error(f"Error fetching Ichimoku data: {req_err}")
    if hasattr(req_err, 'response') and req_err.response is not None:
        try:
            error_detail = req_err.response.json().get('detail', 'Unknown error')
            st.error(f"Server error: {error_detail}")
        except:
            st.error(f"HTTP {req_err.response.status_code} error")
    st.stop()
except ValueError as json_err:
    st.error(f"Error parsing Ichimoku JSON: {json_err}")
    if 'resp_ichi' in locals():
        st.text(f"Response text: {resp_ichi.text[:200]}…")
    st.stop()

# Render the chart
try:
    render_chart(df, df_ichimoku, ticker_name)
except Exception as chart_err:
    st.error(f"Error rendering chart: {chart_err}")
    st.write("**Raw Data Preview:**")
    st.dataframe(df.head())
    st.write("**Ichimoku Data Preview:**")
    st.dataframe(df_ichimoku.head())

# Additional info section
with st.expander("📈 About Ichimoku Cloud", expanded=False):
    st.write("""
    The Ichimoku Cloud (Ichimoku Kinko Hyo) is a comprehensive technical analysis tool that provides:
    
    **Components:**
    - **Tenkan-sen (Conversion Line)**: 9-period high-low average
    - **Kijun-sen (Base Line)**: 26-period high-low average  
    - **Chikou Span (Lagging Span)**: Current close plotted 26 periods back
    - **Senkou Span A (Leading Span A)**: Average of Tenkan and Kijun, plotted 26 periods ahead
    - **Senkou Span B (Leading Span B)**: 52-period high-low average, plotted 26 periods ahead
    
    **The Cloud (Kumo):**
    - **Green Cloud**: Bullish trend (Span A > Span B)
    - **Red Cloud**: Bearish trend (Span B > Span A)
    """)

# AWS status info
if aws_status.get("aws_available", False):
    with st.expander("☁️ AWS Integration Status", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Service Status:**")
            st.write(f"- AWS Available: {'✅' if aws_status.get('aws_available') else '❌'}")
            st.write(f"- S3 Enabled: {'✅' if aws_status.get('s3_enabled') else '❌'}")  
            st.write(f"- S3 Connected: {'✅' if aws_status.get('s3_connected') else '❌'}")
        with col2:
            st.write("**Features:**")
            st.write(f"- Lambda: {'✅' if aws_status.get('lambda_enabled') else '❌'}")
            st.write(f"- CloudWatch: {'✅' if aws_status.get('cloudwatch_enabled') else '❌'}")
            if aws_status.get('bucket_name'):
                st.write(f"- Bucket: `{aws_status['bucket_name']}`")