"""
AWS Lambda Function for Ichimoku Data Collection

This file is for REFERENCE and DEBUGGING purposes only.
The actual Lambda function runs in AWS cloud.

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
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda function to fetch ticker data and store in S3
    
    Expected event format:
    {
        "ticker": "AAPL",
        "bucket_name": "ichimoku-data-bt2025"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "success": true,
            "message": "Successfully processed AAPL",
            "ticker": "AAPL",
            "rows_processed": 251,
            "csv_key": "data/AAPL_2024_data.csv",
            "timestamp": "2024-12-30T..."
        }
    }
    """
    
    try:
        # Parse input
        ticker = event.get('ticker', '').upper().strip()
        bucket_name = event.get('bucket_name', 'ichimoku-data-bt2025')
        
        if not ticker:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Ticker symbol is required'
                })
            }
        
        logger.info(f"Processing ticker: {ticker} for bucket: {bucket_name}")
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Step 1: Fetch data from Yahoo Finance
        logger.info(f"Fetching data for {ticker} from Yahoo Finance...")
        
        try:
            # Fetch 2024 data (adjust date range as needed)
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start="2024-01-01", end="2024-12-31")
            
            if df.empty:
                raise ValueError(f"No data found for ticker {ticker}")
                
            # Format data to match your existing structure
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
                    'error': f'Error fetching data: {str(e)}',
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
            
            # Upload to S3 (overwrites if exists)
            s3_client.put_object(
                Bucket=bucket_name,
                Key=csv_key,
                Body=csv_content,
                ContentType='text/csv'
            )
            
            logger.info(f"Successfully uploaded {csv_key} to S3")
            
        except Exception as e:
            logger.error(f"Error uploading CSV to S3: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': f'Error uploading to S3: {str(e)}',
                    'ticker': ticker
                })
            }
        
        # Step 3: Update ticker list
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
                ContentType='text/plain'
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
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            })
        }

# Local testing function (not used in Lambda)
def test_locally():
    """
    For local debugging only - DO NOT USE IN PRODUCTION
    This function helps debug the logic before uploading to Lambda
    """
    test_event = {
        "ticker": "MSFT",
        "bucket_name": "ichimoku-data-bt2025"
    }
    
    print("🧪 Testing Lambda function logic locally...")
    print("Note: This will use your local AWS credentials")
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    print("⚠️ This file is for AWS Lambda deployment reference only!")
    print("💡 Copy this code into AWS Lambda Console to deploy")
    print("🧪 Uncomment the line below to test logic locally (for debugging)")
    # test_locally()