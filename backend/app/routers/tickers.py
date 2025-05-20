from fastapi import APIRouter, HTTPException
from app.services.data_fetch import fetch_ticker_data
from app.services.ichimoku import apply_ichimoku_cloud
from typing import Optional
import pandas as pd

router = APIRouter()

@router.get("/tickers/{ticker_name}")
async def get_ticker_data(
    ticker_name: str,
    conversion_len: Optional[int] = 9,
    base_len: Optional[int] = 26,
    lagging_len: Optional[int] = 26,
    leading_span_b_len: Optional[int] = 52,
    cloud_shift: Optional[int] = 26
):
    try:
        # Fetch the ticker data
        df = fetch_ticker_data(ticker_name)
        
        # Apply Ichimoku Cloud calculations
        df_ichimoku = apply_ichimoku_cloud(
            df,
            conversion_len=conversion_len,
            base_len=base_len,
            lagging_len=lagging_len,
            leading_span_b_len=leading_span_b_len,
            cloud_shift=cloud_shift
        )
        
        # Convert to dict for JSON response
        df_dict = df.to_dict(orient="records")
        df_ichimoku_dict = df_ichimoku.to_dict(orient="records")
        
        return {
            "ticker_data": df_dict,
            "ichimoku_data": df_ichimoku_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))