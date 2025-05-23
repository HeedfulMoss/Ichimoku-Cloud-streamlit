import boto3
import pandas as pd
import io
import json
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AWSDataService:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3_client = None
        self._initialize_s3_client()
        
    def _initialize_s3_client(self):
        """Initialize S3 client with error handling"""
        try:
            self.s3_client = boto3.client('s3')
            # Test the connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except Exception as e:
            logger.warning(f"Could not connect to S3: {e}")
            self.s3_client = None
    
    def is_available(self):
        """Check if S3 service is available"""
        return self.s3_client is not None
        
    def get_csv_from_s3(self, ticker):
        """Fetch CSV data from S3"""
        if not self.is_available():
            logger.warning("S3 service not available")
            return None
            
        try:
            key = f"data/{ticker}_2024_data.csv"
            logger.info(f"Attempting to fetch {key} from S3")
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            csv_data = response['Body'].read().decode('utf-8')
            
            df = pd.read_csv(io.StringIO(csv_data))
            df.columns = ['time','open','high','low','close','volume']
            df['time'] = pd.to_datetime(df['time'], errors='coerce')
            df['time'] = df['time'].dt.strftime('%Y-%m-%d')
            
            logger.info(f"Successfully fetched {ticker} data from S3 ({len(df)} rows)")
            return df
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"CSV file for {ticker} not found in S3")
            return None
        except Exception as e:
            logger.error(f"Error fetching {ticker} from S3: {e}")
            return None
    
    def cache_api_response(self, ticker, data):
        """Cache API responses in S3 with automatic cleanup"""
        if not self.is_available():
            return False
            
        try:
            key = f"cache/{ticker}_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'ticker': ticker,
                'data': data,
                'count': len(data)
            }
            
            # Cache the data (overwrites same-day cache)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(cache_data),
                ContentType='application/json'
            )
            
            # Clean up old cache files (async cleanup)
            self._cleanup_old_cache(ticker)
            
            logger.info(f"Cached {ticker} data to S3 ({len(data)} records) - expires in 7 days")
            return True
            
        except Exception as e:
            logger.error(f"Error caching {ticker} to S3: {e}")
            return False
    
    def _cleanup_old_cache(self, ticker):
        """Remove cache files older than 7 days for this ticker"""
        try:
            # List cache files for this ticker
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f'cache/{ticker}_'
            )
            
            cutoff_date = datetime.now() - timedelta(days=7)
            files_to_delete = []
            
            for obj in response.get('Contents', []):
                # Extract date from filename: cache/AAPL_2024-01-15.json
                try:
                    date_str = obj['Key'].split('_')[-1].replace('.json', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        files_to_delete.append({'Key': obj['Key']})
                        
                except (ValueError, IndexError):
                    # Skip files that don't match expected pattern
                    continue
            
            # Delete old files in batch
            if files_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': files_to_delete}
                )
                logger.info(f"Cleaned up {len(files_to_delete)} old cache files for {ticker}")
                
        except Exception as e:
            logger.debug(f"Cache cleanup failed (non-critical): {e}")
    
    def cleanup_all_expired_cache(self):
        """Clean up all expired cache files (call this periodically)"""
        if not self.is_available():
            return
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='cache/'
            )
            
            cutoff_date = datetime.now() - timedelta(days=7)
            files_to_delete = []
            
            for obj in response.get('Contents', []):
                try:
                    # Extract date from filename
                    filename = obj['Key'].split('/')[-1]  # Get filename from path
                    date_str = filename.split('_')[-1].replace('.json', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        files_to_delete.append({'Key': obj['Key']})
                        
                except (ValueError, IndexError):
                    continue
            
            if files_to_delete:
                # Delete in batches of 1000 (S3 limit)
                for i in range(0, len(files_to_delete), 1000):
                    batch = files_to_delete[i:i+1000]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': batch}
                    )
                
                logger.info(f"Cleaned up {len(files_to_delete)} expired cache files")
                
        except Exception as e:
            logger.error(f"Global cache cleanup failed: {e}")
    
    def get_cached_data(self, ticker):
        """Get cached data from S3 if it exists and is recent"""
        if not self.is_available():
            return None
            
        try:
            key = f"cache/{ticker}_{datetime.now().strftime('%Y-%m-%d')}.json"
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            cached_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Check if cache is from today
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if cache_time.date() == datetime.now().date():
                logger.info(f"Using cached {ticker} data from S3 ({cached_data.get('count', 0)} records)")
                return cached_data['data']
                
        except self.s3_client.exceptions.NoSuchKey:
            logger.debug(f"No cache found for {ticker}")
        except Exception as e:
            logger.debug(f"Error accessing cache for {ticker}: {e}")
            
        return None
    
    def list_available_data(self):
        """List all available data files in S3"""
        if not self.is_available():
            return []
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='data/'
            )
            
            files = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.csv') and '_2024_data.csv' in key:
                    ticker = key.split('/')[-1].split('_')[0]
                    files.append({
                        'ticker': ticker,
                        'key': key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing S3 data: {e}")
            return []
    
    def get_cache_status(self):
        """Get status of cache files for monitoring"""
        if not self.is_available():
            return {'available': False, 'total_files': 0, 'total_size': 0}
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='cache/'
            )
            
            files = response.get('Contents', [])
            total_size = sum(obj['Size'] for obj in files)
            
            # Group by ticker
            tickers = {}
            for obj in files:
                try:
                    filename = obj['Key'].split('/')[-1]
                    ticker = filename.split('_')[0]
                    if ticker not in tickers:
                        tickers[ticker] = 0
                    tickers[ticker] += 1
                except:
                    continue
            
            return {
                'available': True,
                'total_files': len(files),
                'total_size': total_size,
                'tickers': tickers,
                'size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {'available': False, 'error': str(e)}
    
    def force_cleanup_cache(self):
        """Force cleanup of all cache files (admin function)"""
        if not self.is_available():
            return False
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='cache/'
            )
            
            files_to_delete = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
            
            if files_to_delete:
                # Delete in batches of 1000 (S3 limit)
                deleted_count = 0
                for i in range(0, len(files_to_delete), 1000):
                    batch = files_to_delete[i:i+1000]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': batch}
                    )
                    deleted_count += len(batch)
                
                logger.info(f"Force cleaned up {deleted_count} cache files")
                return True
            else:
                logger.info("No cache files to clean up")
                return True
                
        except Exception as e:
            logger.error(f"Force cache cleanup failed: {e}")
            return False

    # NEW LAMBDA INTEGRATION METHODS

    def get_available_tickers(self):
        """Get list of available tickers from S3"""
        if not self.is_available():
            return []
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key='data/available_tickers.txt'
            )
            ticker_list = response['Body'].read().decode('utf-8').strip()
            tickers = [t.strip() for t in ticker_list.split('\n') if t.strip()]
            logger.info(f"Retrieved {len(tickers)} available tickers from S3")
            return sorted(tickers)
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("No ticker list found in S3")
            return []
        except Exception as e:
            logger.error(f"Error fetching ticker list: {e}")
            return []

    def trigger_lambda_data_collection(self, ticker, lambda_function_name):
        """Trigger Lambda function to collect data for a ticker"""
        if not self.is_available():
            return {"success": False, "error": "S3 not available"}
        
        try:
            # Create Lambda client (will use same AWS credentials as S3)
            lambda_client = boto3.client('lambda')
            
            payload = {
                "ticker": ticker.upper(),
                "bucket_name": self.bucket_name
            }
            
            logger.info(f"Triggering Lambda function {lambda_function_name} for {ticker}")
            
            response = lambda_client.invoke(
                FunctionName=lambda_function_name,
                InvocationType='RequestResponse',  # Synchronous execution
                Payload=json.dumps(payload)
            )
            
            # Parse Lambda response
            response_payload = json.loads(response['Payload'].read().decode('utf-8'))
            
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                logger.info(f"Lambda execution successful for {ticker}: {body.get('message')}")
                return {
                    "success": True,
                    "message": body.get('message', 'Success'),
                    "ticker": ticker,
                    "rows_processed": body.get('rows_processed', 0),
                    "csv_key": body.get('csv_key', ''),
                    "timestamp": body.get('timestamp', '')
                }
            else:
                error_body = json.loads(response_payload.get('body', '{}'))
                logger.error(f"Lambda execution failed for {ticker}: {error_body.get('error')}")
                return {
                    "success": False,
                    "error": error_body.get('error', 'Lambda execution failed'),
                    "ticker": ticker
                }
                
        except Exception as e:
            logger.error(f"Error triggering Lambda for {ticker}: {e}")
            return {
                "success": False,
                "error": f"Failed to trigger data collection: {str(e)}",
                "ticker": ticker
            }

    def check_ticker_data_exists(self, ticker):
        """Check if data for a ticker already exists in S3"""
        if not self.is_available():
            return False
        
        try:
            key = f"data/{ticker}_2024_data.csv"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            logger.error(f"Error checking if {ticker} data exists: {e}")
            return False