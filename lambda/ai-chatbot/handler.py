import json
import boto3
import logging
from datetime import datetime, timedelta
import hashlib
import re
import os

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

s3_client = boto3.client('s3')
logs_client = boto3.client('logs')
bedrock_client = boto3.client('bedrock-runtime', region_name=os.getenv('BEDROCK_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb')

S3_BUCKET = os.getenv('S3_BUCKET_NAME')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
CACHE_TABLE = os.getenv('CACHE_TABLE', 'sre-automation-chatbot-cache')


class LogFetcher:
    """Fetches logs from CloudWatch and S3"""
    
    @staticmethod
    def fetch_cloudwatch_logs(log_group_name, hours_back=1, filter_pattern=None):
        """Fetch logs from CloudWatch"""
        try:
            end_time = int(datetime.utcnow().timestamp() * 1000)
            start_time = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            kwargs = {
                'logGroupName': log_group_name,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 100
            }
            
            if filter_pattern:
                kwargs['filterPattern'] = filter_pattern
            
            response = logs_client.filter_log_events(**kwargs)
            
            events = response.get('events', [])
            logs_text = '\n'.join([event['message'] for event in events])
            
            logger.info(f"Fetched {len(events)} log events from CloudWatch")
            return logs_text
            
        except Exception as e:
            logger.error(f"Error fetching CloudWatch logs: {str(e)}")
            return ""
    
    @staticmethod
    def fetch_s3_logs(bucket, prefix, limit_kb=500):
        """Fetch logs from S3 (latest file)"""
        try:
            # List objects with prefix
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=10
            )
            
            if 'Contents' not in response:
                logger.info(f"No logs found in S3/{prefix}")
                return ""
            
            # Get latest object
            objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
            latest_object = objects[0]
            
            # Fetch object
            obj_response = s3_client.get_object(Bucket=bucket, Key=latest_object['Key'])
            logs_text = obj_response['Body'].read().decode('utf-8')
            
            # Limit size
            if len(logs_text) > limit_kb * 1024:
                logs_text = logs_text[-limit_kb * 1024:]
                logger.warning(f"Truncated S3 logs to {limit_kb}KB")
            
            logger.info(f"Fetched {len(logs_text)} bytes from S3/{latest_object['Key']}")
            return logs_text
            
        except Exception as e:
            logger.error(f"Error fetching S3 logs: {str(e)}")
            return ""


class LogAnalyzer:
    """Analyzes logs and extracts patterns"""
    
    @staticmethod
    def extract_errors(logs_text):
        """Extract error entries"""
        error_pattern = r'(?:ERROR|EXCEPTION|FAILED|error:|failure:)\s*(.+?)(?=\n|$)'
        errors = re.findall(error_pattern, logs_text, re.IGNORECASE)
        return errors
    
    @staticmethod
    def extract_queries(logs_text, user=None):
        """Extract SQL/database queries"""
        query_pattern = r'(?:SELECT|INSERT|UPDATE|DELETE|QUERY)\s+(.+?)(?=;|\n|$)'
        all_queries = re.findall(query_pattern, logs_text, re.IGNORECASE)
        
        if user:
            user_queries = [q for q in all_queries if user.lower() in q.lower()]
            return user_queries
        
        return all_queries
    
    @staticmethod
    def calculate_error_rate(logs_text):
        """Calculate error rate"""
        total_lines = len(logs_text.split('\n'))
        error_lines = len(LogAnalyzer.extract_errors(logs_text))
        
        if total_lines == 0:
            return 0
        
        return (error_lines / total_lines) * 100
    
    @staticmethod
    def detect_anomalies(logs_text):
        """Detect anomalies in logs"""
        anomalies = []
        
        # 1. Error rate spike detection
        error_rate = LogAnalyzer.calculate_error_rate(logs_text)
        if error_rate > 5:
            anomalies.append(f"High error rate detected: {error_rate:.1f}%")
        
        # 2. Timeout detections
        timeouts = len(re.findall(r'timeout|timed out', logs_text, re.IGNORECASE))
        if timeouts > 0:
            anomalies.append(f"Found {timeouts} timeout events")
        
        # 3. Connection errors
        conn_errors = len(re.findall(r'connection\s+(?:refused|reset|timeout)', logs_text, re.IGNORECASE))
        if conn_errors > 0:
            anomalies.append(f"Found {conn_errors} connection errors")
        
        # 4. Out of memory
        if re.search(r'out of memory|OOM|memory.*exceeded', logs_text, re.IGNORECASE):
            anomalies.append("Out of memory condition detected")
        
        # 5. Extremely large logs
        if len(logs_text) > 1000000:
            anomalies.append("Extremely large log volume detected")
        
        return anomalies
    
    @staticmethod
    def summarize_logs(logs_text):
        """Create a summary of log contents"""
        lines = logs_text.split('\n')
        errors = LogAnalyzer.extract_errors(logs_text)
        error_rate = LogAnalyzer.calculate_error_rate(logs_text)
        anomalies = LogAnalyzer.detect_anomalies(logs_text)
        
        summary = {
            'total_lines': len([l for l in lines if l.strip()]),
            'error_count': len(errors),
            'error_rate': f"{error_rate:.2f}%",
            'anomalies': anomalies,
            'sample_errors': errors[:5]
        }
        
        return summary


class AIAnalyzer:
    """Uses Bedrock to analyze logs with AI"""
    
    @staticmethod
    def get_cached_response(query):
        """Check if response is cached"""
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            table = dynamodb.Table(CACHE_TABLE)
            response = table.get_item(Key={'query_hash': query_hash})
            
            if 'Item' in response:
                logger.info(f"Cache hit for query: {query}")
                return response['Item']['response']
        except Exception as e:
            logger.warning(f"Error checking cache: {str(e)}")
        
        return None
    
    @staticmethod
    def cache_response(query, response):
        """Cache AI response"""
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            table = dynamodb.Table(CACHE_TABLE)
            
            table.put_item(Item={
                'query_hash': query_hash,
                'query': query,
                'response': response,
                'timestamp': int(datetime.utcnow().timestamp()),
                'expiration_time': int(datetime.utcnow().timestamp()) + (24 * 3600)  # 24h TTL
            })
            logger.info("Response cached")
        except Exception as e:
            logger.warning(f"Error caching response: {str(e)}")
    
    @staticmethod
    def analyze_with_bedrock(logs_text, query):
        """Use Bedrock to analyze logs"""
        try:
            # Check cache first
            cached = AIAnalyzer.get_cached_response(query)
            if cached:
                return cached
            
            # Build user message with full logs for metric extraction
            if logs_text:
                user_message = f"""Task: Answer this question ONLY using data from the logs below.

LOGS:
{logs_text}

QUESTION: {query}

INSTRUCTIONS:
1. Look for metrics (CPU, Memory, Disk usage with percentages)
2. Extract EXACT numbers and percentages
3. Answer ONLY what is in the logs
4. If data exists, provide specific values
5. If data does NOT exist, say "No [metric] data in logs"
6. Be concise - 1-3 sentences maximum"""
            else:
                user_message = query
            
            # Prepare system prompt
            system_prompt = """You are an infrastructure metric extraction expert. Analyze logs precisely.

When asked about metrics (CPU, Memory, Disk):
- Extract EXACT percentages shown in logs
- Always provide current, average, and peak if available
- Format: "Current X%, Average Y%, Peak Z%"
- If logs show metrics, ALWAYS mention them
- Never say "no data" if the logs contain it

Task: Extract and report infrastructure metrics from logs. Be accurate."""
            
            # Use Bedrock Converse API for Nova models (correct format)
            response = bedrock_client.converse(
                modelId=BEDROCK_MODEL_ID,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'text': user_message
                            }
                        ]
                    }
                ],
                system=[
                    {
                        'text': system_prompt
                    }
                ],
                inferenceConfig={
                    'maxTokens': 2048,
                    'temperature': 0.7
                }
            )
            
            ai_response = response['output']['message']['content'][0]['text']
            
            # Cache the response
            AIAnalyzer.cache_response(query, ai_response)
            
            logger.info("AI analysis complete")
            return ai_response
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock: {str(e)}")
            return f"Error: {str(e)}"


def handle_predefined_queries(query_type, logs_text, dbuser=None, time_range=1):
    """Handle predefined query types with rule-based analysis"""
    
    if query_type == "queries_by_user":
        queries = LogAnalyzer.extract_queries(logs_text, user=dbuser)
        if queries:
            return {
                'type': 'queries_by_user',
                'user': dbuser,
                'count': len(queries),
                'samples': queries[:5],
                'full_list': queries
            }
        return {
            'type': 'queries_by_user',
            'user': dbuser,
            'count': 0,
            'message': f"No queries found for user {dbuser}"
        }
    
    elif query_type == "recent_errors":
        errors = LogAnalyzer.extract_errors(logs_text)
        if errors:
            return {
                'type': 'recent_errors',
                'time_range_hours': time_range,
                'count': len(errors),
                'errors': errors
            }
        return {
            'type': 'recent_errors',
            'time_range_hours': time_range,
            'count': 0,
            'message': "No errors found"
        }
    
    elif query_type == "error_rate_trend":
        error_rate = LogAnalyzer.calculate_error_rate(logs_text)
        return {
            'type': 'error_rate_trend',
            'error_rate': f"{error_rate:.2f}%",
            'is_increasing': error_rate > 5,
            'threshold': 5,
            'recommendation': 'Monitor logs closely' if error_rate > 5 else 'All good'
        }
    
    elif query_type == "anomalies":
        anomalies = LogAnalyzer.detect_anomalies(logs_text)
        return {
            'type': 'anomalies',
            'count': len(anomalies),
            'anomalies': anomalies
        }
    
    return None


def process_query(query, logs_text):
    """Process user query and provide answer"""
    
    # Check for predefined queries
    if 'query' in query.lower() and 'user' in query.lower():
        match = re.search(r'user[:\s]+(\w+)', query, re.IGNORECASE)
        if match:
            return handle_predefined_queries('queries_by_user', logs_text, dbuser=match.group(1))
    
    if 'error' in query.lower() and 'last' in query.lower():
        match = re.search(r'last\s+(\d+)\s+(?:hour|minute)', query, re.IGNORECASE)
        time_range = int(match.group(1)) if match else 1
        return handle_predefined_queries('recent_errors', logs_text, time_range=time_range)
    
    if 'error rate' in query.lower() and ('increasing' in query.lower() or 'trend' in query.lower()):
        return handle_predefined_queries('error_rate_trend', logs_text)
    
    if 'anomal' in query.lower():
        return handle_predefined_queries('anomalies', logs_text)
    
    # Fall back to AI analysis
    ai_response = AIAnalyzer.analyze_with_bedrock(logs_text, query)
    return {
        'type': 'ai_analysis',
        'query': query,
        'response': ai_response
    }


def lambda_handler(event, context):
    """
    AI Chatbot Lambda handler
    
    Supports two modes:
    
    1. Log Analysis (Default - REST API):
    POST /ask with {"question": "What errors occurred?"}
    - Automatically fetches logs from S3 (default) or CloudWatch
    - Analyzes logs
    - Answers based on actual data
    
    2. Override Log Source (Optional):
    {
        "query": "What errors in last 2 hours?",
        "log_source": "cloudwatch",  # or "s3"
        "log_group": "/aws/lambda/sre-automation-sre-agent",
        "s3_prefix": "logs/",
        "time_range_hours": 2
    }
    """
    logger.info(f"Request: {json.dumps(event)}")
    
    try:
        # Parse request
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        else:
            body = event
        
        query = body.get('query') or body.get('question')
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'query parameter required'})
            }
        
        # Log analysis mode (default for API)
        # Allow user to override log source, otherwise use S3 as default
        log_source = body.get('log_source', 's3')  # Default to S3 instead of cloudwatch
        log_group = body.get('log_group', '/aws/lambda/sre-automation-sre-agent')
        s3_prefix = body.get('s3_prefix', 'logs/')
        time_range = body.get('time_range_hours', 1)
        
        logger.info(f"Fetching logs from {log_source} for analysis")
        
        # Fetch logs
        logs_text = ""
        if log_source == 's3':
            logs_text = LogFetcher.fetch_s3_logs(S3_BUCKET, s3_prefix)
        else:
            logs_text = LogFetcher.fetch_cloudwatch_logs(log_group, hours_back=time_range)
        
        if not logs_text:
            logger.warning("No logs found in specified source")
            # Fall back to general AI analysis if no logs available
            logger.info("Falling back to general AI analysis")
            ai_response = AIAnalyzer.analyze_with_bedrock("", query)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'query': query,
                    'note': 'No logs found in database/S3. Providing general AI analysis.',
                    'analysis': {
                        'type': 'ai_analysis_fallback',
                        'query': query,
                        'response': ai_response
                    }
                }),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Create log summary
        summary = LogAnalyzer.summarize_logs(logs_text)
        logger.info(f"Log summary: {json.dumps(summary, default=str)}")
        
        # Process query with logs
        result = process_query(query, logs_text)
        
        response = {
            'statusCode': 200,
            'query': query,
            'log_summary': summary,
            'logs_analyzed': True,
            'analysis': result
        }
        
        logger.info(f"Response: {json.dumps(response, default=str)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response, default=str),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
