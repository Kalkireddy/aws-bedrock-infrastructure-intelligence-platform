# AI Log Analysis Chatbot

Uses Amazon Bedrock to intelligently analyze logs and answer questions.

## Capabilities

### 1. Predefined Query Types (Rule-based)
- **Query by User**: `"What query was run by user dbuser1 at this time?"`
- **Recent Errors**: `"What errors occurred in the last 1 hour?"`
- **Error Rate Trend**: `"Is error rate increasing?"`
- **Anomaly Detection**: `"Show anomalies in logs"`

### 2. Free-form Questions (AI-powered with Bedrock)
- Any custom question about log contents
- AI provides detailed analysis with specific references

### 3. Caching
- Responses cached in DynamoDB for common queries
- 24-hour TTL reduces Bedrock API calls

## Log Sources

- **CloudWatch**: Real-time application logs from CloudWatch Log Groups
- **S3**: Historical logs stored in S3 buckets

## Example Requests

```bash
# Via API Gateway
curl -X POST https://api-endpoint.com/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What errors occurred in the last 2 hours?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/sre-automation-sre-agent",
    "time_range_hours": 2
  }'

# Via CLI (local testing)
python -c "
import json
from handler import lambda_handler
event = {
    'query': 'Show me all errors',
    'log_source': 'cloudwatch',
    'log_group': '/aws/lambda/sre-automation-sre-agent'
}
print(json.dumps(lambda_handler(event, None), indent=2))
"
```

## Analysis Features

1. **Error Extraction**: Finds all ERROR/EXCEPTION/FAILED entries
2. **Query Parsing**: Extracts SQL/database queries
3. **Error Rate Calculation**: Computes error percentage
4. **Anomaly Detection**:
   - High error rate (>5%)
   - Timeout events
   - Connection errors
   - Out of memory conditions
   - Unusually large logs

## Bedrock Integration

Uses Claude 3 Sonnet model for:
- Context-aware analysis
- Pattern recognition
- Troubleshooting recommendations
- Code issue identification

Response format: Clear, actionable insights with specific log references.
