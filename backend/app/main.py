from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
import logging

from app.data_fetch import fetch_ticker_data
from app.ichimoku import apply_ichimoku_cloud

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("ichimoku-backend")

# Initialize FastAPI app
app = FastAPI(title="Ichimoku Cloud API", 
              description="Backend API for Ichimoku Cloud Chart Application",
              version="1.0.0")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Root endpoint for API health check"""
    return {"status": "healthy", "message": "Ichimoku Cloud API is running"}
@app.get("/data/{ticker_name}")
async def get_data(ticker_name: str) -> Dict[str, Any]:
    """
    Fetch raw OHLCV for a given ticker.
    """
    try:
        df = fetch_ticker_data(ticker_name)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_name}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching data")

@app.get("/ichimoku/{ticker_name}")
async def get_ichimoku(
    ticker_name: str,
    conversion_len: int = 9,
    base_len: int = 26,
    lagging_len: int = 26,
    leading_span_b_len: int = 52,
    cloud_shift: int = 26
) -> Dict[str, Any]:
    """
    Fetch raw OHLCV and apply Ichimoku Cloud with the given parameters.
    """
    try:
        df = fetch_ticker_data(ticker_name)
        ichimoku_df = apply_ichimoku_cloud(
            df,
            conversion_len=conversion_len,
            base_len=base_len,
            lagging_len=lagging_len,
            leading_span_b_len=leading_span_b_len,
            cloud_shift=cloud_shift
        )
        return {"status": "success", "data": ichimoku_df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Error computing Ichimoku for {ticker_name}: {e}")
        raise HTTPException(status_code=500, detail="Error computing Ichimoku")
    

# Optional additional endpoints for Ichimoku calculations on the backend
# (if you want to move calculations from frontend to backend)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)