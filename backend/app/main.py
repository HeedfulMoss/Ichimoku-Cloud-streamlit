from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
import logging
import os
from pydantic import BaseModel
from datetime import datetime, timedelta
import re
import time

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
    description="Backend API for Ichimoku Cloud Chart Application with AWS S3 and Lambda Integration",
    version="1.3.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SECURITY: Rate limiting storage (in production, use Redis or database)
rate_limit_storage = {}

def is_rate_limited(client_ip: str, endpoint: str) -> bool:
    """
    SECURITY: Rate limiting - max 5 requests per minute per IP per endpoint
    """
    key = f"{client_ip}:{endpoint}"
    now = datetime.now()
    
    if key not in rate_limit_storage:
        rate_limit_storage[key] = []
    
    # Clean old requests (older than 1 minute)
    rate_limit_storage[key] = [
        req_time for req_time in rate_limit_storage[key] 
        if now - req_time < timedelta(minutes=1)
    ]
    
    # Check if under limit
    if len(rate_limit_storage[key]) >= 5:
        return True
    
    # Record this request
    rate_limit_storage[key].append(now)
    return False

def validate_ticker_input(ticker: str) -> tuple[bool, str]:
    """
    SECURITY: Validate ticker input on backend
    """
    if not ticker or not isinstance(ticker, str):
        return False, "Ticker must be a non-empty string"
    
    ticker = ticker.upper().strip()
    
    if len(ticker) < 1 or len(ticker) > 5:
        return False, "Ticker must be 1-5 characters long"
    
    if not re.match(r'^[A-Z0-9]+$', ticker):
        return False, "Ticker must contain only letters and numbers"
    
    blacklist = ['TEST', 'SPAM', 'HACK', 'NULL', 'ADMIN', 'DELETE', 'DROP', 'EXEC']
    if ticker in blacklist:
        return False, f"Ticker '{ticker}' is not allowed"
    
    return True, ticker

# AWS Configuration
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "")
USE_AWS_S3 = os.getenv("USE_AWS_S3", "true").lower() == "true"
USE_AWS_LAMBDA = os.getenv("USE_AWS_LAMBDA", "false").lower() == "true"
USE_AWS_CLOUDWATCH = os.getenv("USE_AWS_CLOUDWATCH", "false").lower() == "true"
AWS_LAMBDA_FUNCTION_NAME = os.getenv("AWS_LAMBDA_FUNCTION_NAME", "ichimoku-data-collector")

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
        "aws_cloudwatch_enabled": USE_AWS_CLOUDWATCH,
        "version": "1.3.0",
        "security": "enhanced"
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
        "lambda_function_name": AWS_LAMBDA_FUNCTION_NAME if USE_AWS_LAMBDA else None,
        "cloudwatch_enabled": USE_AWS_CLOUDWATCH
    }

@app.get("/aws/data")
async def list_s3_data():
    """List available data in S3"""
    if not aws_service:
        raise HTTPException(status_code=503, detail="AWS S3 not available")
    
    files = aws_service.list_available_data()
    return {"status": "success", "files": files}

# LAMBDA ENDPOINTS (SECURED)

@app.get("/aws/tickers")
async def list_available_tickers():
    """List available tickers in S3"""
    if not aws_service:
        raise HTTPException(status_code=503, detail="AWS S3 not available")
    
    tickers = aws_service.get_available_tickers()
    return {
        "status": "success",
        "tickers": tickers,
        "count": len(tickers)
    }

@app.post("/aws/collect/{ticker}")
async def collect_ticker_data(ticker: str, request: Request):
    """
    Trigger Lambda function to collect data for a ticker - SECURED
    """
    # SECURITY: Get client IP for rate limiting
    client_ip = request.client.host
    
    # SECURITY: Rate limiting check
    if is_rate_limited(client_ip, "collect"):
        logger.warning(f"Rate limit exceeded for IP {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please wait before making another request."
        )
    
    if not aws_service:
        raise HTTPException(status_code=503, detail="AWS S3 not available")
    
    if not USE_AWS_LAMBDA:
        raise HTTPException(status_code=503, detail="AWS Lambda not enabled")
    
    if not AWS_LAMBDA_FUNCTION_NAME:
        raise HTTPException(status_code=503, detail="Lambda function name not configured")
    
    # SECURITY: Validate ticker input
    is_valid, result = validate_ticker_input(ticker)
    if not is_valid:
        logger.warning(f"Invalid ticker from IP {client_ip}: {result}")
        raise HTTPException(status_code=400, detail=result)
    
    ticker = result  # Use validated ticker
    
    # Check if data already exists
    data_exists = aws_service.check_ticker_data_exists(ticker)
    
    try:
        logger.info(f"Triggering data collection for {ticker} from IP {client_ip} (exists: {data_exists})")
        
        # SECURITY: Pass source validation parameter
        result = aws_service.trigger_lambda_data_collection(
            ticker, 
            AWS_LAMBDA_FUNCTION_NAME,
            source="ichimoku-app"  # Add source parameter
        )
        
        if result["success"]:
            status_message = f"Successfully collected data for {ticker}"
            if data_exists:
                status_message += " (updated existing data)"
            
            return {
                "status": "success",
                "message": status_message,
                "ticker": result["ticker"],
                "rows_processed": result.get("rows_processed", 0),
                "csv_key": result.get("csv_key", ""),
                "data_existed": data_exists,
                "timestamp": result.get("timestamp", "")
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error in collect_ticker_data for {ticker} from IP {client_ip}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/aws/lambda/status")
async def get_lambda_status():
    """Check Lambda service status"""
    return {
        "lambda_enabled": USE_AWS_LAMBDA,
        "function_name": AWS_LAMBDA_FUNCTION_NAME if USE_AWS_LAMBDA else None,
        "s3_available": aws_service is not None,
        "aws_available": AWS_AVAILABLE
    }

@app.get("/aws/ticker/{ticker}/exists")
async def check_ticker_exists(ticker: str, request: Request):
    """Check if data for a ticker exists in S3"""
    # SECURITY: Rate limiting for data access
    client_ip = request.client.host
    if is_rate_limited(client_ip, "check"):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please wait before making another request."
        )
    
    if not aws_service:
        raise HTTPException(status_code=503, detail="AWS S3 not available")
    
    # SECURITY: Validate ticker input
    is_valid, validated_ticker = validate_ticker_input(ticker)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validated_ticker)
    
    exists = aws_service.check_ticker_data_exists(validated_ticker)
    
    return {
        "status": "success",
        "ticker": validated_ticker,
        "exists": exists
    }

# EXISTING DATA ENDPOINTS (enhanced with security)

@app.get("/data/{ticker_name}")
async def get_data(
    ticker_name: str,
    request: Request,
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
    """
    
    # SECURITY: Rate limiting for data access
    client_ip = request.client.host
    if is_rate_limited(client_ip, "data"):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please wait before making another request."
        )

    # SECURITY: Validate ticker input
    is_valid, validated_ticker = validate_ticker_input(ticker_name)
    if not is_valid:
        logger.warning(f"Invalid ticker from IP {client_ip}: {validated_ticker}")
        raise HTTPException(status_code=400, detail=validated_ticker)
    
    ticker_name = validated_ticker
    logger.info(f"Fetching data for {ticker_name} from IP {client_ip} (use_s3={use_s3}, use_csv={use_csv}, use_cache={use_cache})")
    
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
        
        if aws_service:
            # Check if we have this ticker in S3
            if aws_service.check_ticker_data_exists(ticker_name):
                suggestions.append("try using 'Use AWS S3 Data' option")
            else:
                suggestions.append("try collecting data using Lambda first")
        
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
async def get_ichimoku(req: IchimokuRequest, request: Request) -> Dict[str, Any]:
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
    """
    
    # SECURITY: Rate limiting for calculations
    client_ip = request.client.host
    if is_rate_limited(client_ip, "ichimoku"):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please wait before making another request."
        )
    
    try:
        logger.info(f"Calculating Ichimoku for {len(req.data)} data points from IP {client_ip}")
        
        # SECURITY: Validate data size to prevent abuse
        if len(req.data) > 5000:  # Limit to 5000 data points
            raise HTTPException(
                status_code=413, 
                detail="Data too large. Maximum 5000 data points allowed."
            )
        
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
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error computing Ichimoku: {e}")
        raise HTTPException(status_code=500, detail="Error computing Ichimoku indicators")


# Health check endpoint with more detailed info
@app.get("/health")
async def health_check():
    """Detailed health check including AWS status"""
    health_status = {
        "status": "healthy",
        "api_version": "1.3.0",
        "security_version": "enhanced",
        "services": {
            "yahoo_finance": "available",
            "ichimoku_calculation": "available",
            "aws_s3": "available" if aws_service else "disabled",
            "aws_lambda": "enabled" if USE_AWS_LAMBDA else "disabled", 
            "aws_cloudwatch": "enabled" if USE_AWS_CLOUDWATCH else "disabled",
            "rate_limiting": "enabled",
            "input_validation": "enabled"
        }
    }
    
    # Test S3 connection if available
    if aws_service:
        try:
            files = aws_service.list_available_data()
            tickers = aws_service.get_available_tickers()
            health_status["services"]["aws_s3"] = f"connected ({len(files)} files, {len(tickers)} tickers)"
        except Exception:
            health_status["services"]["aws_s3"] = "connection_error"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)