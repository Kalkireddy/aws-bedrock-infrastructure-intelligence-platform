import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda')
CHATBOT_FUNCTION = "sre-automation-ai-chatbot"

def lambda_handler(event, context):
    """
    API Gateway handler for SRE AI Chatbot
    Accepts POST requests with questions and returns AI analysis
    """
    
    try:
        # Log incoming request
        logger.info(f"API Request: {event}")
        
        # Parse request
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
        path = event.get("rawPath", "/")
        
        # Handle OPTIONS for CORS
        if http_method == "OPTIONS":
            return cors_response(200, {"message": "OK"})
        
        # Parse body
        if event.get("body"):
            body = json.loads(event["body"])
        else:
            body = json.loads(event.get("isBase64Encoded") and 
                            __import__("base64").b64decode(event.get("body", "{}")) or "{}")
        
        question = body.get("question") or body.get("query")
        
        if not question:
            return cors_response(400, {
                "error": "Missing 'question' or 'query' parameter",
                "example": "POST /ask with {'question': 'Why is CPU high?'}"
            })
        
        # Invoke AI Chatbot Lambda to analyze logs
        response = lambda_client.invoke(
            FunctionName=CHATBOT_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                "query": question,
                "log_source": "s3",  # Default to S3 logs
                "s3_prefix": "logs/",  # Default S3 prefix
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        # Parse Lambda response
        response_payload = json.loads(response["Payload"].read().decode())
        
        logger.info(f"Chatbot response: {json.dumps(response_payload, default=str)}")
        logger.info(f"Chatbot response type: {type(response_payload)}")
        
        # Extract the actual AI response text from log analysis
        answer_text = ""
        log_summary = {}
        
        if isinstance(response_payload, dict):
            # If response has 'body' field (Lambda returning full response structure)
            if "body" in response_payload:
                try:
                    body_data = json.loads(response_payload["body"])
                    # Try to get analysis response
                    if "analysis" in body_data:
                        analysis = body_data["analysis"]
                        if isinstance(analysis, dict):
                            answer_text = analysis.get("response", "")
                        else:
                            answer_text = str(analysis)
                    # Get log summary if available
                    if "log_summary" in body_data:
                        log_summary = body_data["log_summary"]
                except:
                    answer_text = response_payload["body"]
            # If response has 'analysis' field directly
            elif "analysis" in response_payload:
                analysis = response_payload["analysis"]
                if isinstance(analysis, dict):
                    answer_text = analysis.get("response", "")
                else:
                    answer_text = str(analysis)
            
            # Get log summary if available
            if "log_summary" in response_payload:
                log_summary = response_payload["log_summary"]
        
        return cors_response(200, {
            "question": question,
            "answer": answer_text or "Unable to generate response",
            "log_summary": log_summary if log_summary else None,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return cors_response(400, {"error": "Invalid JSON in request body"})
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return cors_response(500, {
            "error": "Internal server error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

def cors_response(status_code, body):
    """Format response with CORS headers"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,GET,OPTIONS"
        },
        "body": json.dumps(body)
    }
