#!/bin/bash
# Test script for AI Chatbot Lambda function

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$REPO_ROOT/lambda/ai-chatbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}AI Chatbot Lambda Testing${NC}"
echo "=========================="

# Check if we're testing locally or against AWS
if [ "$1" == "--local" ]; then
    echo -e "\n${YELLOW}Local Testing Mode${NC}"
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 not found${NC}"
        exit 1
    fi
    
    # Install dependencies
    echo -e "\n${YELLOW}Installing dependencies...${NC}"
    pip3 install -q boto3 python-dateutil
    
    # Create test event
    TEST_EVENT=$(cat <<EOF
{
    "query": "What errors occurred in the last 1 hour?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/sre-automation-sre-agent",
    "time_range_hours": 1
}
EOF
)
    
    echo -e "\n${YELLOW}Test Event:${NC}"
    echo "$TEST_EVENT" | python3 -m json.tool
    
    echo -e "\n${YELLOW}Running Lambda handler locally...${NC}"
    
    # Run the test
    python3 << 'PYTHON_TEST'
import sys
import json
sys.path.insert(0, '/Volumes/DevOps-SSD/Projects/FREELANCE/repo-root/lambda/ai-chatbot')

from handler import lambda_handler

test_event = {
    "query": "What errors occurred in the last 1 hour?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/sre-automation-sre-agent",
    "time_range_hours": 1
}

print("Testing with event:")
print(json.dumps(test_event, indent=2))
print("\nExecuting lambda_handler...\n")

try:
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2, default=str))
    print(f"\n✓ Test passed!")
except Exception as e:
    print(f"✗ Test failed: {str(e)}")
    import traceback
    traceback.print_exc()
PYTHON_TEST

else
    # AWS Testing Mode
    if [ -z "$AWS_REGION" ]; then
        AWS_REGION="us-east-1"
    fi
    
    if [ -z "$LAMBDA_FUNCTION_NAME" ]; then
        LAMBDA_FUNCTION_NAME="sre-automation-ai-chatbot"
    fi
    
    echo -e "\n${YELLOW}AWS Testing Mode${NC}"
    echo "Region: $AWS_REGION"
    echo "Function: $LAMBDA_FUNCTION_NAME"
    
    # Generate sample logs first
    echo -e "\n${YELLOW}Generating sample logs...${NC}"
    python3 "$SCRIPT_DIR/generate-sample-logs.py" \
        --type combined \
        --count 100 \
        --cloudwatch-group "/aws/lambda/$LAMBDA_FUNCTION_NAME" \
        --cloudwatch-stream "sample-logs"
    
    # Test 1: Query by user
    echo -e "\n${YELLOW}Test 1: Query by User${NC}"
    TEST_PAYLOAD=$(cat <<EOF
{
    "query": "What query was run by user appuser?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/$LAMBDA_FUNCTION_NAME",
    "time_range_hours": 1
}
EOF
)
    
    aws lambda invoke \
        --region "$AWS_REGION" \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --payload "$TEST_PAYLOAD" \
        --log-type Tail \
        /tmp/test1-response.json
    
    echo "Response:"
    jq '.' /tmp/test1-response.json 2>/dev/null || cat /tmp/test1-response.json
    
    # Test 2: Recent errors
    echo -e "\n${YELLOW}Test 2: Recent Errors${NC}"
    TEST_PAYLOAD=$(cat <<EOF
{
    "query": "What errors occurred in the last 2 hours?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/$LAMBDA_FUNCTION_NAME",
    "time_range_hours": 2
}
EOF
)
    
    aws lambda invoke \
        --region "$AWS_REGION" \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --payload "$TEST_PAYLOAD" \
        --log-type Tail \
        /tmp/test2-response.json
    
    echo "Response:"
    jq '.' /tmp/test2-response.json 2>/dev/null || cat /tmp/test2-response.json
    
    # Test 3: Error rate trend
    echo -e "\n${YELLOW}Test 3: Error Rate Trend${NC}"
    TEST_PAYLOAD=$(cat <<EOF
{
    "query": "Is the error rate increasing?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/$LAMBDA_FUNCTION_NAME",
    "time_range_hours": 1
}
EOF
)
    
    aws lambda invoke \
        --region "$AWS_REGION" \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --payload "$TEST_PAYLOAD" \
        --log-type Tail \
        /tmp/test3-response.json
    
    echo "Response:"
    jq '.' /tmp/test3-response.json 2>/dev/null || cat /tmp/test3-response.json
    
    # Test 4: Anomalies
    echo -e "\n${YELLOW}Test 4: Anomaly Detection${NC}"
    TEST_PAYLOAD=$(cat <<EOF
{
    "query": "Show me all anomalies in logs",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/$LAMBDA_FUNCTION_NAME",
    "time_range_hours": 1
}
EOF
)
    
    aws lambda invoke \
        --region "$AWS_REGION" \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --payload "$TEST_PAYLOAD" \
        --log-type Tail \
        /tmp/test4-response.json
    
    echo "Response:"
    jq '.' /tmp/test4-response.json 2>/dev/null || cat /tmp/test4-response.json
fi

echo -e "\n${GREEN}✓ Testing complete!${NC}"
