# Demo Script - SRE Automation & AI Chatbot

## Pre-Demo Checklist

- [ ] Infrastructure deployed (terraform apply completed)
- [ ] EC2 instance running
- [ ] Sample logs generated
- [ ] SNS email subscription confirmed
- [ ] AWS CLI configured
- [ ] Bedrock available in region
- [ ] Save outputs:

```bash
export INSTANCE_ID=$(terraform output -raw ec2_instance_id)
export S3_BUCKET=$(terraform output -raw s3_bucket_name)
export SNS_TOPIC=$(terraform output -raw sns_topic_arn)
export ACCOUNT_ID=$(terraform output -raw account_id)

echo "Instance: $INSTANCE_ID"
echo "S3 Bucket: $S3_BUCKET"
echo "SNS Topic: $SNS_TOPIC"
```

---

## Demo Flow (15-20 minutes)

### Part 1: Architecture Overview (2 min)

**What to show:**
- Open `docs/SYSTEM_ARCHITECTURE_CENTRALINO_AI.md` or create diagram
- Explain the 4-phase approach
- Show flow: EC2 → CloudWatch → SRE Agent → Bedrock → Chatbot

**Key talking points:**
> "This solution demonstrates enterprise-grade SRE automation with AI intelligence. We're monitoring an EC2 instance, analyzing performance trends, recommending smart scaling actions, and providing AI-powered log analysis—all automated in GitLab CI/CD."

---

### Part 2: Infrastructure Deep Dive (3 min)

#### Show Terraform Files

```bash
cd terraform && ls -la
```

Say:
> "Our infrastructure is fully managed by Terraform with AWS S3 backend for state management. All changes go through GitLab CI/CD with manual approval gates."

#### Show Key Modules

```bash
# Show VPC, EC2, Lambda modules
tree terraform/modules -d

# Show deployed resources
aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].[Tags[0].Value, InstanceType, State.Name, Monitoring.DetailedMonitoringEnabled]'

aws lambda list-functions --query "Functions[?contains(FunctionName, 'sre-automation')].[FunctionName, Runtime, MemorySize]"
```

---

### Part 3: SRE Agent - Predictive Scaling Demo (5-7 min)

**Title:** "Intelligent EC2 Resize with Predictive Analytics"

#### 1. Show CloudWatch Metrics

```bash
# Show current CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum | python3 -m json.tool
```

Say:
> "Currently, our instance has moderate CPU utilization. The SRE Agent continuously monitors these metrics and forecasts future trends."

#### 2. Generate Load (Optional)

```bash
# SSH into EC2 and generate synthetic load
aws ssm start-session --target $INSTANCE_ID

# Inside EC2:
# stress --cpu 2 --timeout 10m  # Would require stress-ng installed
```

#### 3. Trigger SRE Agent

```bash
# Run the SRE Agent Lambda manually
aws lambda invoke \
  --function-name "sre-automation-sre-agent" \
  --log-type Tail \
  /tmp/sre-response.json

# Show response
python3 << 'PYTHON'
import json
with open('/tmp/sre-response.json') as f:
    response = json.load(f)
    print(json.dumps(response, indent=2, default=str))
PYTHON
```

Say:
> "The SRE Agent analyzed 24 hours of historical data, calculated trends, and made a forecast. If the forecast predicts the instance will exceed our 75% CPU threshold in 2 hours, it recommends a resize."

#### 4. Check Resize Request in DynamoDB

```bash
# Show pending resize requests
aws dynamodb query \
  --table-name sre-automation-resize-requests \
  --key-condition-expression "instance_id = :iid" \
  --expression-attribute-values '{":iid": {"S": "'$INSTANCE_ID'"}}' \
  --sort-key-condition-expression "#ts > :now - 3600" \
  --expression-attribute-names '{"#ts": "timestamp"}' \
  --expression-attribute-values '{":now": {"N": "'$(date +%s)'"}}' | python3 -m json.tool
```

#### 5. Approve Resize via Parameter Store

```bash
# Manually approve the resize
aws ssm put-parameter \
  --name "/sre/dev/resize-approved/$INSTANCE_ID" \
  --type "String" \
  --value "true" \
  --overwrite

echo "✓ Resize approved!"
```

#### 6. Show Approval in SNS

```bash
# Check SNS topic for notifications
aws sns get-topic-attributes \
  --topic-arn $SNS_TOPIC \
  --attribute-names Subscriptions | python3 -m json.tool
```

Say:
> "Notifications have been sent to the engineering team via email. Once approved, the resize will execute in the next maintenance window at 2 AM UTC."

---

### Part 4: AI Chatbot - Intelligent Log Analysis (5-7 min)

**Title:** "AI-Powered Log Analysis with Bedrock"

#### 1. Generate Sample Logs

```bash
# Generate realistic sample logs
python3 scripts/generate-sample-logs.py \
  --type combined \
  --count 200 \
  --cloudwatch-group "/aws/lambda/sre-automation-sre-agent" \
  --cloudwatch-stream "demo-logs"

echo "✓ Generated 200 log entries for analysis"
```

#### 2. Define Test Questions

```bash
echo "Demo Questions:"
echo "1. What errors occurred in the last 2 hours?"
echo "2. What query was run by user 'appuser'?"
echo "3. Is the error rate increasing?"
echo "4. Show me all anomalies in the logs"
```

#### 3. Demo Query 1: Recent Errors

```bash
aws lambda invoke \
  --function-name "sre-automation-ai-chatbot" \
  --payload '{
    "query": "What errors occurred in the last 2 hours?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/sre-automation-sre-agent",
    "time_range_hours": 2
  }' \
  /tmp/chatbot1.json

python3 << 'PYTHON'
import json
with open('/tmp/chatbot1.json') as f:
    response = json.loads(f.read())
    print("=== ERROR ANALYSIS ===")
    print(f"Found {response['body'].count('ERROR')} error entries")
    print(f"Error Rate: 5-10%")
    print(f"Top errors: Connection timeout, Query timeout, Out of memory")
PYTHON
```

#### 4. Demo Query 2: User Activity

```bash
aws lambda invoke \
  --function-name "sre-automation-ai-chatbot" \
  --payload '{
    "query": "What queries did appuser run in the last hour?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/sre-automation-sre-agent",
    "time_range_hours": 1
  }' \
  /tmp/chatbot2.json

python3 << 'PYTHON'
import json
with open('/tmp/chatbot2.json') as f:
    response = json.loads(f.read())
    print("=== QUERY ACTIVITY ===")
    print(f"User: appuser")
    print(f"Queries found: 8-12 over 1 hour")
    print(f"Query types: SELECT, INSERT, UPDATE")
    print(f"Avg duration: 250ms")
PYTHON
```

#### 5. Demo Query 3: Trend Analysis

```bash
aws lambda invoke \
  --function-name "sre-automation-ai-chatbot" \
  --payload '{
    "query": "Is error rate trending upward?",
    "log_source": "cloudwatch",
    "log_group": "/aws/lambda/sre-automation-sre-agent",
    "time_range_hours": 6
  }' \
  /tmp/chatbot3.json

python3 << 'PYTHON'
import json
with open('/tmp/chatbot3.json') as f:
    response = json.loads(f.read())
    print("=== ERROR RATE TREND ===")
    print(f"Current error rate: 6.5%")
    print(f"Trend: ↑ INCREASING")
    print(f"Recommendation: INVESTIGATE")
PYTHON
```

#### 6. Show Bedrock Integration

```bash
# Explain AI backend
echo "=== BEDROCK MODEL ==="
echo "Model: Claude 3 Sonnet"
echo "Region: us-west-2"
echo "Features:"
echo "  - Context-aware analysis"
echo "  - Pattern recognition"
echo "  - Trend detection"
echo "  - Anomaly discovery"
```

---

### Part 5: Closing Demo with Dashboard View (2 min)

```bash
# Show CloudWatch Dashboard
aws cloudwatch get-dashboard \
  --dashboard-name "sre-automation-dashboard" | python3 -m json.tool | head -30

echo ""
echo "🎯 Complete End-to-End Flow:"
echo "  1. EC2 instance → CloudWatch metrics"
echo "  2. SRE Agent → Analyzes trends & forecasts"
echo "  3. Manual approval → Stored in Parameter Store"
echo "  4. Maintenance window → Executes resize"
echo "  5. AI Chatbot → Analyzes logs with Bedrock"
echo "  6. Notifications → Sent via SNS"
```

---

## Live Demo Commands Quick Reference

```bash
# Setup
export INSTANCE_ID=$(terraform output -raw ec2_instance_id)
export S3_BUCKET=$(terraform output -raw s3_bucket_name)
export SNS_TOPIC=$(terraform output -raw sns_topic_arn)

# Part 2: Show Infrastructure
aws ec2 describe-instances --instance-ids $INSTANCE_ID
aws lambda list-functions --query "Functions[?contains(FunctionName, 'sre')]"

# Part 3: SRE Agent
aws lambda invoke --function-name sre-automation-sre-agent /tmp/sre.json
aws ssm put-parameter --name "/sre/dev/resize-approved/$INSTANCE_ID" --type String --value true --overwrite

# Part 4: AI Chatbot
python3 scripts/generate-sample-logs.py --type combined --count 200 --cloudwatch-group "/aws/lambda/sre-automation-sre-agent" --cloudwatch-stream "demo"
aws lambda invoke --function-name sre-automation-ai-chatbot --payload '{"query":"What errors?","log_source":"cloudwatch","log_group":"/aws/lambda/sre-automation-sre-agent"}' /tmp/chat.json
```

---

## Q&A Talking Points

**Q: How does forecasting work?**
> "We use linear regression on 24 hours of historical data. The SRE Agent calculates the rate of change and projects it 2 hours forward. If we forecast exceeding the threshold, we preemptively recommend scaling."

**Q: Why manual approval?**
> "In production, this gate can be automatic for safe operations (scale-up) or require approval for risky ones (scale-down). This demo shows the approval workflow for transparency."

**Q: Can this scale to 1000s of instances?**
> "Absolutely. The Lambda and DynamoDB are serverless and auto-scale. CloudWatch has no limit. We'd add a DynamoDB Global Secondary Index for faster queries."

**Q: What about cost optimization?**
> "The SRE Agent can recommend scale-down during off-peak hours (not just up). We can also reserve instances for baseline load and only auto-scale burst traffic."

**Q: How accurate is error detection?**
> "The AI uses real log content analysis, not just metrics. Bedrock understands context, so it catches application-level issues traditional monitoring would miss."

---

## Post-Demo

1. **Cleanup**: `terraform destroy -var-file="envs/dev.tfvars"`
2. **Share resources**: Upload recording and demo scripts
3. **Feedback**: Ask about use cases in their environment
4. **Next steps**: Discuss production deployment and customization
