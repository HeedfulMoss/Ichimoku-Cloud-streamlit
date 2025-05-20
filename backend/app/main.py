# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.data_fetch import fetch_ticker_data
from app.ichimoku import apply_ichimoku_cloud

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/api/ichimoku/{ticker}")
def get_ichimoku(
    ticker: str,
    conversion_len: int = 9,
    base_len: int = 26,
    lagging_len: int = 26,
    leading_span_b_len: int = 52,
    cloud_shift: int = 26,
):
    # 1) fetch raw OHLCV
    df = fetch_ticker_data(ticker)

    # 2) compute Ichimoku lines
    df_ich = apply_ichimoku_cloud(
        df,
        conversion_len=conversion_len,
        base_len=base_len,
        lagging_len=lagging_len,
        leading_span_b_len=leading_span_b_len,
        cloud_shift=cloud_shift,
    )

    # 3) return both as JSON
    return {
        "data":       df.to_dict(orient="records"),
        "ichimoku":   df_ich.to_dict(orient="records"),
    }
