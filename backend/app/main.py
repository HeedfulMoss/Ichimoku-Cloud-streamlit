
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
import logging
import os
from pydantic import BaseModel

from app.data_fetch import fetch_ticker_data
from app.ichimoku import apply_ichimoku_cloud

# AWS imports with fallback
try:
    from app.aws_data_service import AWSDataService
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("ichimoku-backend")

# Initialize FastAPI app
app = FastAPI(
    title="Ichimoku Cloud API", 
    description="Backend API for Ichimoku Cloud Chart Application with AWS S3 Integration",
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

# AWS Configuration
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "")
USE_AWS_S3 = os.getenv("USE_AWS_S3", "true").lower() == "true"
USE_AWS_LAMBDA = os.getenv("USE_AWS_LAMBDA", "false").lower() == "true"
USE_AWS_CLOUDWATCH = os.getenv("USE_AWS_CLOUDWATCH", "false").lower() == "true"

# Initialize AWS service only if configured and enabled
aws_service = None
if AWS_AVAILABLE and USE_AWS_S3 and AWS_BUCKET_NAME:
    try:
        aws_service = AWSDataService(AWS_BUCKET_NAME)
        if not aws_service.is_available():
            aws_service = None
            logger.warning("AWS S3 service not available - continuing without S3")
        else:
            logger.info(f"AWS S3 service initialized with bucket: {AWS_BUCKET_NAME}")
    except Exception as e:
        logger.warning(f"Failed to initialize AWS service: {e}")
        aws_service = None
else:
    logger.info("AWS S3 integration disabled or not configured")

@app.get("/")
def read_root():
    """Root endpoint for API health check"""
    return {
        "status": "healthy", 
        "message": "Ichimoku Cloud API is running",
        "aws_s3_enabled": aws_service is not None,
        "aws_lambda_enabled": USE_AWS_LAMBDA,
        "aws_cloudwatch_enabled": USE_AWS_CLOUDWATCH
    }

@app.get("/aws/status")
async def get_aws_status():
    """Check AWS service availability"""
    return {
        "aws_available": AWS_AVAILABLE,
        "s3_enabled": USE_AWS_S3,
        "s3_connected": aws_service is not None,
        "bucket_name": AWS_BUCKET_NAME if aws_service else None,
        "lambda_enabled": USE_AWS_LAMBDA,
        "cloudwatch_enabled": USE_AWS_CLOUDWATCH
    }

@app.get("/aws/data")
async def list_s3_data():
    """List available data in S3"""
    if not aws_service:
        raise HTTPException(status_code=503, detail="AWS S3 not available")
    
    files = aws_service.list_available_data()
    return {"status": "success", "files": files}

@app.get("/data/{ticker_name}")
async def get_data(
    ticker_name: str, 
    use_csv: bool = Query(False, description="Use local CSV backup data"),
    use_s3: bool = Query(False, description="Use AWS S3 data"),
    use_cache: bool = Query(True, description="Use S3 cache if available")
) -> Dict[str, Any]:
    """
    Fetch raw OHLCV for a given ticker with multiple data source options.
    
    Data Source Priority:
    1. S3 Cache (if use_s3=true and use_cache=true)
    2. S3 CSV files (if use_s3=true) 
    3. Local CSV backup (if use_csv=true and ticker=AAPL)
    4. Yahoo Finance API (with optional S3 caching)
    
    Example usage:
    - /data/AAPL - Yahoo Finance with S3 caching
    - /data/AAPL?use_s3=true - Try S3 first, fallback to Yahoo Finance  
    - /data/AAPL?use_csv=true - Use local CSV backup
    - /data/MSFT?use_s3=true&use_cache=false - S3 CSV only, no cache

    Example:
    [{'time': '2024-01-02', 'open': 185.78945295661444, 'high': 187.07008341179338, 'low': 182.55315792151214, 'close': 184.29043579101562, 'volume': 82488700}, {'time': '2024-01-03', 'open': 182.88075702582086, 'high': 184.52869277861944, 'low': 182.09649169200898, 'close': 182.91053771972656, 'volume': 58414500}, {'time': '2024-01-04', 'open': 180.82578520690032, 'high': 181.7589539428833, 'low': 179.5650288616003, 'close': 180.58753967285156, 'volume': 71983600}, {'time': '2024-01-05', 'open': 180.66696287937032, 'high': 181.43135417752765, 'low': 178.86018676112266, 'close': 179.8628387451172, 'volume': 62303300}, {'time': '2024-01-08', 'open': 180.76622380895435, 'high': 184.2507162227342, 'low': 180.18051667398524, 'close': 184.21099853515625, 'volume': 59144500}]
    """


    ticker_name = ticker_name.upper()
    logger.info(f"Fetching data for {ticker_name} (use_s3={use_s3}, use_csv={use_csv}, use_cache={use_cache})")
    
    # Try S3 cache first (if enabled and requested)
    if use_s3 and use_cache and aws_service:
        cached_data = aws_service.get_cached_data(ticker_name)
        if cached_data:
            logger.info(f"Returning cached data for {ticker_name}")
            return {
                "status": "success", 
                "data": cached_data, 
                "source": "s3_cache",
                "ticker": ticker_name,
                "count": len(cached_data)
            }
    
    # Try S3 CSV backup (if enabled and requested)
    if use_s3 and aws_service:
        df = aws_service.get_csv_from_s3(ticker_name)
        if df is not None:
            data = df.to_dict(orient="records")
            logger.info(f"Returning S3 CSV data for {ticker_name}")
            return {
                "status": "success", 
                "data": data, 
                "source": "s3_csv",
                "ticker": ticker_name,
                "count": len(data)
            }
    
    # Try local CSV backup (existing logic for AAPL only)
    if use_csv and ticker_name == "AAPL":
        try:
            df = fetch_ticker_data(ticker_name, use_csv=True)
            data = df.to_dict(orient="records")
            logger.info(f"Returning local CSV data for {ticker_name}")
            return {
                "status": "success", 
                "data": data, 
                "source": "local_csv",
                "ticker": ticker_name,
                "count": len(data)
            }
        except Exception as e:
            logger.warning(f"Local CSV fallback failed: {e}")

    # Try Yahoo Finance API (existing logic)
    try:
        df = fetch_ticker_data(ticker_name, use_csv=False)
        data = df.to_dict(orient="records")
        
        # Cache successful API calls to S3 (if enabled and we got data)
        if aws_service and len(data) > 0:
            cache_success = aws_service.cache_api_response(ticker_name, data)
            if cache_success:
                logger.info(f"Cached {ticker_name} data to S3")
        
        logger.info(f"Returning Yahoo Finance data for {ticker_name}")
        return {
            "status": "success", 
            "data": data, 
            "source": "yahoo_finance",
            "ticker": ticker_name,
            "count": len(data)
        }
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_name}: {e}")
        
        # Provide helpful error message with suggestions
        error_msg = f"Error fetching data for {ticker_name}"
        suggestions = []
        
        if aws_service and ticker_name != "AAPL":
            suggestions.append("try uploading CSV data to S3")
        if ticker_name != "AAPL":
            suggestions.append("try using AAPL ticker")
        if not aws_service:
            suggestions.append("enable AWS S3 integration")
            
        if suggestions:
            error_msg += f". Suggestions: {', '.join(suggestions)}"
            
        raise HTTPException(status_code=500, detail=error_msg)

# Pydantic model for Ichimoku request (unchanged from original)
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
    Apply Ichimoku Cloud calculations with the given parameters.
    
    This endpoint takes raw OHLCV data and calculates all Ichimoku indicators:
    - Tenkan-sen (Conversion Line)  
    - Kijun-sen (Base Line)
    - Chikou Span (Lagging Span)
    - Senkou Span A (Leading Span A) 
    - Senkou Span B (Leading Span B)
    - Cloud color based on span relationship
    
    The calculation logic is identical to the original implementation.

    Example:
    [{'time': '2024-01-02', 'open': 185.78945295661444, 'high': 187.07008341179338, 'low': 182.55315792151214, 'close': 184.29043579101562, 'volume': 82488700.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 186.95095825195312, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-03', 'open': 182.88075702582086, 'high': 184.52869277861944, 'low': 182.09649169200898, 'close': 182.91053771972656, 'volume': 58414500.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 187.71632385253906, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-04', 'open': 180.82578520690032, 'high': 181.7589539428833, 'low': 179.5650288616003, 'close': 180.58753967285156, 'volume': 71983600.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 186.02650451660156, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-05', 'open': 180.66696287937032, 'high': 181.43135417752765, 'low': 178.86018676112266, 'close': 179.8628387451172, 'volume': 62303300.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 183.92918395996094, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}, {'time': '2024-01-08', 'open': 180.76622380895435, 'high': 184.2507162227342, 'low': 180.18051667398524, 'close': 184.21099853515625, 'volume': 59144500.0, 'tenkan_sen': nan, 'kijun_sen': nan, 'chikou_span': 183.0445098876953, 'senkou_span_a': nan, 'senkou_span_b': nan, 'cloud_color': 'rgba(255,182,193,0.3)'}]

    """
    try:
        logger.info(f"Calculating Ichimoku for {len(req.data)} data points")
        
        # Convert request data to DataFrame
        df = pd.DataFrame(req.data)
        
        # Apply Ichimoku calculations using existing logic
        ich_df = apply_ichimoku_cloud(
            df,
            conversion_len=req.conversion_len,
            base_len=req.base_len,
            lagging_len=req.lagging_len,
            leading_span_b_len=req.leading_span_b_len,
            cloud_shift=req.cloud_shift
        )
        
        # Convert result back to dict format
        result_data = ich_df.to_dict(orient="records")
        
        logger.info(f"Successfully calculated Ichimoku indicators")
        logger.debug(f"Sample result: {result_data[:2] if len(result_data) > 0 else 'No data'}")
        
        return {
            "status": "success", 
            "data": result_data,
            "parameters": {
                "conversion_len": req.conversion_len,
                "base_len": req.base_len,
                "lagging_len": req.lagging_len,
                "leading_span_b_len": req.leading_span_b_len,
                "cloud_shift": req.cloud_shift
            },
            "count": len(result_data)
        }
        
    except Exception as e:
        logger.error(f"Error computing Ichimoku: {e}")
        raise HTTPException(status_code=500, detail=f"Error computing Ichimoku: {str(e)}")


# Health check endpoint with more detailed info
@app.get("/health")
async def health_check():
    """Detailed health check including AWS status"""
    health_status = {
        "status": "healthy",
        "api_version": "1.0.0",
        "services": {
            "yahoo_finance": "available",
            "ichimoku_calculation": "available",
            "aws_s3": "available" if aws_service else "disabled",
            "aws_lambda": "enabled" if USE_AWS_LAMBDA else "disabled", 
            "aws_cloudwatch": "enabled" if USE_AWS_CLOUDWATCH else "disabled"
        }
    }
    
    # Test S3 connection if available
    if aws_service:
        try:
            files = aws_service.list_available_data()
            health_status["services"]["aws_s3"] = f"connected ({len(files)} files)"
        except Exception:
            health_status["services"]["aws_s3"] = "connection_error"
    
    return health_status

# Optional: Keep the old endpoint commented for reference
# @app.get("/ichimoku/{ticker_name}")  
# This endpoint was replaced by the two-step process: /data/{ticker} + POST /ichimoku
# This provides more flexibility and follows REST conventions better

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)