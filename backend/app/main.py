from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
import logging
from pydantic import BaseModel

from app.data_fetch import fetch_ticker_data
from app.ichimoku import apply_ichimoku_cloud

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("ichimoku-backend")

# Initialize FastAPI app
app = FastAPI(
    title="Ichimoku Cloud API", 
    description="Backend API for Ichimoku Cloud Chart Application",
    version="1.0.0"
)

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
async def get_data(ticker_name: str, use_csv: bool = Query(False, description="Use CSV backup data instead of Yahoo Finance")) -> Dict[str, Any]:
    """
    Fetch raw OHLCV for a given ticker.
    Example in print statement (for debugging):
    [{'time': '2024-01-02', 'open': 185.78945295661444, 'high': 187.07008341179338, 'low': 182.55315792151214, 'close': 184.29043579101562, 'volume': 82488700}, {'time': '2024-01-03', 'open': 182.88075702582086, 'high': 184.52869277861944, 'low': 182.09649169200898, 'close': 182.91053771972656, 'volume': 58414500}, {'time': '2024-01-04', 'open': 180.82578520690032, 'high': 181.7589539428833, 'low': 179.5650288616003, 'close': 180.58753967285156, 'volume': 71983600}, {'time': '2024-01-05', 'open': 180.66696287937032, 'high': 181.43135417752765, 'low': 178.86018676112266, 'close': 179.8628387451172, 'volume': 62303300}, {'time': '2024-01-08', 'open': 180.76622380895435, 'high': 184.2507162227342, 'low': 180.18051667398524, 'close': 184.21099853515625, 'volume': 59144500}]
    """
    if ticker_name is "AAPL" and use_csv:
        df = fetch_ticker_data(ticker_name, use_csv=use_csv)
        print("DEBUG get_data – df.head():")
        print(df.head().to_dict(orient="records"))
        return {"status": "success", "data": df.to_dict(orient="records")}

    try:
        df = fetch_ticker_data(ticker_name)
        print("DEBUG get_data – df.head():")
        print(df.head().to_dict(orient="records"))
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_name}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching data")

class IchimokuRequest(BaseModel):
    data: List[Dict[str, Any]]
    conversion_len: int = 9
    base_len: int = 26
    lagging_len: int = 26
    leading_span_b_len: int = 52
    cloud_shift: int = 26

@app.post("/ichimoku")
async def get_ichimoku(req: IchimokuRequest) -> Dict[str, Any]:
    """
    Apply Ichimoku Cloud with the given parameters.
    Example in print statement:
    [{'time': '2024-01-02', 'open': 185.78945295661444, 'high': 187.07008341179338, 'low': 182.55315792151214, 'close': 184.29043579101562, 'volume': 82488700.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 186.95095825195312, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-03', 'open': 182.88075702582086, 'high': 184.52869277861944, 'low': 182.09649169200898, 'close': 182.91053771972656, 'volume': 58414500.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 187.71632385253906, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-04', 'open': 180.82578520690032, 'high': 181.7589539428833, 'low': 179.5650288616003, 'close': 180.58753967285156, 'volume': 71983600.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 186.02650451660156, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-05', 'open': 180.66696287937032, 'high': 181.43135417752765, 'low': 178.86018676112266, 'close': 179.8628387451172, 'volume': 62303300.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 183.92918395996094, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-08', 'open': 180.76622380895435, 'high': 184.2507162227342, 'low': 180.18051667398524, 'close': 184.21099853515625, 'volume': 59144500.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 183.0445098876953, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}]
    """
    try:
        df = pd.DataFrame(req.data)
        ich_df = apply_ichimoku_cloud(
            df,
            conversion_len=req.conversion_len,
            base_len=req.base_len,
            lagging_len=req.lagging_len,
            leading_span_b_len=req.leading_span_b_len,
            cloud_shift=req.cloud_shift
        )
        logger.debug("DEBUG get_ichimoku sample: %s", ich_df.head().to_dict(orient="records"))
        return {"status": "success", "data": ich_df.to_dict(orient="records")}
    except Exception as e:
        logger.error("Error computing Ichimoku: %s", e)
        raise HTTPException(status_code=500, detail="Error computing Ichimoku")

# @app.get("/ichimoku/{ticker_name}")
# async def get_ichimoku(
#     ticker_name: str,
#     conversion_len: int = 9,
#     base_len: int = 26,
#     lagging_len: int = 26,
#     leading_span_b_len: int = 52,
#     cloud_shift: int = 26
# ) -> Dict[str, Any]:
#     """
#     Fetch raw OHLCV and apply Ichimoku Cloud with the given parameters.
#     Example in print statement:
#     [{'time': '2024-01-02', 'open': 185.78945295661444, 'high': 187.07008341179338, 'low': 182.55315792151214, 'close': 184.29043579101562, 'volume': 82488700.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 186.95095825195312, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-03', 'open': 182.88075702582086, 'high': 184.52869277861944, 'low': 182.09649169200898, 'close': 182.91053771972656, 'volume': 58414500.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 187.71632385253906, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-04', 'open': 180.82578520690032, 'high': 181.7589539428833, 'low': 179.5650288616003, 'close': 180.58753967285156, 'volume': 71983600.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 186.02650451660156, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-05', 'open': 180.66696287937032, 'high': 181.43135417752765, 'low': 178.86018676112266, 'close': 179.8628387451172, 'volume': 62303300.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 183.92918395996094, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-08', 'open': 180.76622380895435, 'high': 184.2507162227342, 'low': 180.18051667398524, 'close': 184.21099853515625, 'volume': 59144500.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 183.0445098876953, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}]
#     """
#     try:
#         df = fetch_ticker_data(ticker_name)
#         ichimoku_df = apply_ichimoku_cloud(
#             df,
#             conversion_len=conversion_len,
#             base_len=base_len,
#             lagging_len=lagging_len,
#             leading_span_b_len=leading_span_b_len,
#             cloud_shift=cloud_shift
#         )
#         print("DEBUG get_ichimoku – ichimoku_df.head():")
#         print(ichimoku_df.head().to_dict(orient="records"))
#         return {"status": "success", "data": ichimoku_df.to_dict(orient="records")}
#     except Exception as e:
#         logger.error(f"Error computing Ichimoku for {ticker_name}: {e}")
#         raise HTTPException(status_code=500, detail="Error computing Ichimoku")
    

# Optional additional endpoints for Ichimoku calculations on the backend
# (if you want to move calculations from frontend to backend)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)