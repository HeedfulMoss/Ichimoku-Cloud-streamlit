"""
AWS Lambda Function for Ichimoku Data Collection - SECURED VERSION

This file is for REFERENCE and DEBUGGING purposes only.
The actual Lambda function runs in AWS cloud.

SECURITY IMPROVEMENTS:
- Hardcoded bucket name (no parameter injection)
- Input validation for ticker symbols
- Source validation requirement
- Rate limiting protection
- Size limits to prevent abuse
- Enhanced error handling

To deploy:
1. Copy this code into AWS Lambda Console
2. Set up dependencies manually via console
3. Test via console

DO NOT execute this file locally - it's designed for AWS Lambda environment.
"""

import json
import boto3
import pandas as pd
import yfinance as yf
import io
import re
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SECURITY: Hardcode bucket name - don't accept as parameter
ALLOWED_BUCKET = "ichimoku-data-bt2025"

# SECURITY: Rate limiting tracking (in-memory for this execution)
RATE_LIMIT_CALLS = 0
MAX_CALLS_PER_EXECUTION = 1  # Only process 1 ticker per invocation

def validate_ticker(ticker):
    """
    SECURITY: Validate ticker symbol format
    Only allow: A-Z, 1-5 characters, common stock symbols
    """
    if not ticker or not isinstance(ticker, str):
        return False, "Ticker must be a non-empty string"
    
    ticker = ticker.upper().strip()
    
    # Length check
    if len(ticker) < 1 or len(ticker) > 5:
        return False, "Ticker must be 1-5 characters long"
    
    # Character check - only letters and numbers
    if not re.match(r'^[A-Z0-9]+$', ticker):
        return False, "Ticker must contain only letters and numbers"
    
    # Blacklist check for obvious bad inputs
    blacklist = ['TEST', 'SPAM', 'HACK', 'NULL', 'ADMIN', 'DELETE', 'DROP', 'EXEC']
    if ticker in blacklist:
        return False, f"Ticker '{ticker}' is not allowed"
    
    return True, ticker

def lambda_handler(event, context):
    """
    AWS Lambda function to fetch ticker data and store in S3 - SECURED
    
    Expected event format:
    {
        "ticker": "AAPL",
        "source": "ichimoku-app"  # SECURITY: Require source identifier
    }
    
    SECURITY CHANGES:
    - Removed bucket_name parameter (hardcoded)
    - Added ticker validation
    - Added source validation
    - Added rate limiting
    - Enhanced error handling
    - Added size limits
    """
    
    global RATE_LIMIT_CALLS
    
    try:
        # SECURITY: Rate limiting check
        RATE_LIMIT_CALLS += 1
        if RATE_LIMIT_CALLS > MAX_CALLS_PER_EXECUTION:
            return {
                'statusCode': 429,
                'body': json.dumps({
                    'success': False,
                    'error': 'Rate limit exceeded - too many requests'
                })
            }
        
        # SECURITY: Validate source
        source = event.get('source', '').strip()
        if source != 'ichimoku-app':
            logger.warning(f"Invalid source: {source}")
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'success': False,
                    'error': 'Invalid request source'
                })
            }
        
        # SECURITY: Validate ticker
        ticker_input = event.get('ticker', '')
        is_valid, result = validate_ticker(ticker_input)
        if not is_valid:
            logger.warning(f"Invalid ticker validation: {result}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': f'Invalid ticker: {result}'
                })
            }
        
        ticker = result  # Use validated ticker
        bucket_name = ALLOWED_BUCKET  # SECURITY: Use hardcoded bucket
        
        logger.info(f"Processing validated ticker: {ticker} for bucket: {bucket_name}")
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # SECURITY: Verify bucket exists and we have access
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except Exception as e:
            logger.error(f"Bucket access denied or not found: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': 'Storage service unavailable'
                })
            }
        
        # Step 1: Fetch data from Yahoo Finance with timeout
        logger.info(f"Fetching data for {ticker} from Yahoo Finance...")
        
        try:
            # SECURITY: Add timeout to prevent hanging
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(
                start="2024-01-01", 
                end="2024-12-31",
                timeout=30  # 30 second timeout
            )
            
            if df.empty:
                # This might be a real ticker with no 2024 data, not necessarily malicious
                logger.info(f"No 2024 data found for ticker {ticker}")
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'success': False,
                        'error': f'No 2024 data available for ticker {ticker}',
                        'ticker': ticker
                    })
                }
                
            # Format data to match existing structure
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].reset_index()
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d')
            
            logger.info(f"Successfully fetched {len(df)} rows for {ticker}")
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': 'Data fetching service unavailable',
                    'ticker': ticker
                })
            }
        
        # Step 2: Convert to CSV and upload to S3
        csv_key = f"data/{ticker}_2024_data.csv"
        
        try:
            # Convert DataFrame to CSV string
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
            
            # SECURITY: Limit CSV size to prevent abuse
            if len(csv_content) > 1024 * 1024:  # 1MB limit
                logger.warning(f"CSV too large for {ticker}: {len(csv_content)} bytes")
                return {
                    'statusCode': 413,
                    'body': json.dumps({
                        'success': False,
                        'error': 'Data too large to process',
                        'ticker': ticker
                    })
                }
            
            # Upload to S3 (overwrites if exists)
            s3_client.put_object(
                Bucket=bucket_name,
                Key=csv_key,
                Body=csv_content,
                ContentType='text/csv',
                ServerSideEncryption='AES256'  # SECURITY: Encrypt at rest
            )
            
            logger.info(f"Successfully uploaded {csv_key} to S3")
            
        except Exception as e:
            logger.error(f"Error uploading CSV to S3: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': 'Storage service error',
                    'ticker': ticker
                })
            }
        
        # Step 3: Update ticker list (with size limits)
        try:
            ticker_list_key = "data/available_tickers.txt"
            
            # Try to get existing ticker list
            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=ticker_list_key)
                existing_tickers = response['Body'].read().decode('utf-8').strip().split('\n')
                existing_tickers = [t.strip() for t in existing_tickers if t.strip()]
            except s3_client.exceptions.NoSuchKey:
                existing_tickers = []
                logger.info("No existing ticker list found, creating new one")
            
            # SECURITY: Limit total number of tickers
            if len(existing_tickers) >= 100 and ticker not in existing_tickers:
                logger.warning(f"Ticker limit reached: {len(existing_tickers)}")
                return {
                    'statusCode': 507,
                    'body': json.dumps({
                        'success': False,
                        'error': 'Storage limit reached - too many tickers',
                        'ticker': ticker
                    })
                }
            
            # Add new ticker if not already present
            if ticker not in existing_tickers:
                existing_tickers.append(ticker)
                existing_tickers.sort()  # Keep list sorted alphabetically
                logger.info(f"Added {ticker} to ticker list")
            else:
                logger.info(f"{ticker} already exists in ticker list")
            
            # Upload updated ticker list
            ticker_list_content = '\n'.join(existing_tickers)
            s3_client.put_object(
                Bucket=bucket_name,
                Key=ticker_list_key,
                Body=ticker_list_content,
                ContentType='text/plain',
                ServerSideEncryption='AES256'  # SECURITY: Encrypt at rest
            )
            
            logger.info(f"Updated ticker list with {len(existing_tickers)} tickers")
            
        except Exception as e:
            logger.warning(f"Error updating ticker list: {str(e)} (non-critical)")
            # Don't fail the whole operation if ticker list update fails
        
        # Step 4: Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'message': f'Successfully processed {ticker}',
                'ticker': ticker,
                'rows_processed': len(df),
                'csv_key': csv_key,
                'timestamp': datetime.now().isoformat(),
                'bucket': bucket_name  # Confirm which bucket was used
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': 'Internal service error'  # SECURITY: Don't expose internal details
            })
        }

# Local testing function (for debugging)
def test_locally():
    """
    For local debugging only - DO NOT USE IN PRODUCTION
    """
    test_event = {
        "ticker": "MSFT",
        "source": "ichimoku-app"  # Required source validation
    }
    
    print("🧪 Testing secured Lambda function logic locally...")
    print("Note: This will use your local AWS credentials")
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    print("⚠️ This file is for AWS Lambda deployment reference only!")
    print("💡 Copy this SECURED code into AWS Lambda Console to deploy")
    print("🔒 This version includes security improvements")
    print("🧪 Uncomment the line below to test logic locally (for debugging)")
    # test_locally()