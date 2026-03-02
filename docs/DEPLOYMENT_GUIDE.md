# SRE Automation & AI Chatbot - Deployment Guide

## Prerequisites

- AWS Account with lab/sandbox environment
- GitLab account and repository access
- AWS CLI v2 configured with credentials
- Terraform >= 1.0
- Python 3.11+
- bash shell

## Architecture Overview

This solution implements a complete SRE automation platform with 4 phases:

1. **Terraform + GitLab CI/CD**: Infrastructure as Code with automated deployment
2. **EC2 Resize Automation**: Intelligent resource scaling with predictive analytics (every 2 hours)
3. **S3 Metric Logging**: Automatic metric collection and storage (CPU/Memory/Disk percentages)
4. **AI Log Analysis**: AWS Bedrock Nova Pro-powered log intelligence and anomaly detection
5. **REST API**: API Gateway endpoint for interactive chatbot queries
6. **Demo & Documentation**: Full operational runbook

## Phase 1: Infrastructure Deployment

### Step 1.1: Initialize Terraform

```bash
cd terraform
terraform init -upgrade

# Select environment (dev or prod)
terraform workspace new dev
terraform workspace select dev
```

### Step 1.2: Configure AWS Credentials

```bash
# Set AWS credentials via environment or AWS CLI
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### Step 1.3: Customize Variables

Edit `terraform/terraform.auto.tfvars` (create if not exists):

```hcl
aws_region              = "us-east-1"
environment             = "dev"
project_name            = "sre-automation"
sns_email              = "your-email@example.com"  # For notifications
min_cpu_threshold      = 75
instance_type          = "t3.micro"
```

### Step 1.4: Plan Deployment

```bash
terraform plan -var-file="envs/dev.tfvars" -out=tfplan.dev

# Review the plan output
cat tfplan.dev | grep -E "^(~|+|-)"  # Show changes
```

### Step 1.5: Apply Infrastructure

```bash
terraform apply tfplan.dev

# Save outputs
terraform output -json > terraform-outputs.json
```

### Outputs to Note

```bash
# Get these values for later use
aws_account_id=$(terraform output -raw account_id)
sns_topic_arn=$(terraform output -raw sns_topic_arn)
s3_bucket=$(terraform output -raw s3_bucket_name)
ec2_instance=$(terraform output -raw ec2_instance_id)
lambda_sre=$(terraform output -raw lambda_sre_agent_arn)
lambda_chatbot=$(terraform output -raw lambda_ai_chatbot_arn)

echo "Account ID: $aws_account_id"
echo "SNS Topic: $sns_topic_arn"
echo "S3 Bucket: $s3_bucket"
echo "EC2 Instance: $ec2_instance"
```

## Phase 2: GitLab CI/CD Setup

### Step 2.1: Create GitLab Project

```bash
# Push to your GitLab instance
git remote add origin https://gitlab.com/your-org/sre-automation.git
git branch -M main
git push -uf origin main
```

### Step 2.2: Configure Runners

In GitLab Project Settings → CI/CD → Runners:
- Register a runner with shell executor and docker support
- Or use GitLab's shared runners

### Step 2.3: Set CI/CD Variables

In GitLab Project Settings → CI/CD → Variables:

```
AWS_ACCESS_KEY_ID          (masked)
AWS_SECRET_ACCESS_KEY      (masked)
AWS_DEFAULT_REGION         us-east-1
TF_ROOT                    terraform
```

### Step 2.4: Test Pipeline

Create a merge request and watch GitLab CI run:
1. `validate` stage - validates Terraform syntax
2. `plan` stage - creates execution plan
3. `apply` stage - **manual approval required** - applies changes

## Phase 3: EC2 and CloudWatch Setup

### Step 3.1: Verify EC2 Instance

```bash
aws ec2 describe-instances \
  --instance-ids $ec2_instance \
  --query 'Reservations[0].Instances[0].[InstanceId,State.Name,InstanceType]'
```

### Step 3.2: Configure EC2 CloudWatch Agent

The EC2 instance launches with CloudWatch agent configured via user data. It:
- Pushes CPU, memory, disk metrics to CloudWatch
- Streams logs to CloudWatch Logs
- Runs a sample application that generates test logs

### Step 3.3: Verify Alarms

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "sre-automation" \
  --query 'MetricAlarms[*].[AlarmName,StateValue]'
```

## Phase 4: SRE Agent Configuration

### Step 4.1: Verify EventBridge Schedule

The SRE Agent runs automatically every 2 hours via EventBridge:

```bash
# Verify the EventBridge rule
aws events describe-rule \
  --name sre-automation-sre-agent-schedule \
  --query '[State, ScheduleExpression]'

# Expected output:
# ["ENABLED", "rate(2 hours)"]
```

### Step 4.2: Deploy Sample Logs

Generate test data for the SRE Agent:

```bash
python3 scripts/generate-sample-logs.py \
  --type combined \
  --count 200 \
  --cloudwatch-group "/aws/ec2/sre-automation" \
  --cloudwatch-stream "sample-logs"
```

### Step 4.3: Trigger SRE Agent Manually

```bash
# First, ensure Lambda has environment variables set
# These should be configured by Terraform, but verify:

aws lambda get-function-configuration \
  --function-name "sre-automation-sre-agent" \
  --query 'Environment.Variables'

# Invoke the function manually
aws lambda invoke \
  --function-name "sre-automation-sre-agent" \
  --log-type Tail \
  /tmp/sre-agent-response.json

# Check response (will include S3 save confirmation)
cat /tmp/sre-agent-response.json | python3 -m json.tool

# Verify metrics saved to S3
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/logs/ --recursive
```

### Step 4.4: Check S3 Metric Logs

The SRE Agent saves formatted metric logs every 2 hours:

```bash
# Read the latest metric log
aws s3 cp s3://$(terraform output -raw s3_bucket_name)/logs/latest-metrics.txt - | head -20

# Expected format:
# METRICS:
#   CPU Usage:
#     - Current: 58.18%
#     - Average: 48.82%
#     - Peak: 62.21%
#   Memory Usage:
#     - Current: 77.98%
#     - Average: 45.45%
#     - Peak: 87.09%
```

### Step 4.5: Approve Resize Request

When SRE Agent recommends a resize, approve it via Parameter Store:

```bash
# Get the instance ID
instance_id=$(terraform output -raw ec2_instance_id)

# Check pending requests
aws dynamodb query \
  --table-name sre-automation-resize-requests \
  --key-condition-expression "instance_id = :iid" \
  --expression-attribute-values '{":iid": {"S": "'$instance_id'"}}'

# Approve resize
aws ssm put-parameter \
  --name "/sre/dev/resize-approved/$instance_id" \
  --type "String" \
  --value "true" \
  --overwrite

echo "✓ Resize approved for $instance_id"
```

### Step 4.4: Trigger Maintenance Window

```bash
# Manually trigger the resize (normally runs at 2 AM UTC)
aws lambda invoke \
  --function-name "sre-automation-maintenance-window" \
  --log-type Tail \
  /tmp/maintenance-response.json

# Check results
cat /tmp/maintenance-response.json | python3 -m json.tool
```

## Phase 5: API Gateway & Bedrock Integration

### Step 5.1: Verify API Gateway Setup

```bash
# Get API Gateway ID
API_GATEWAY_ID=$(terraform output -raw api_gateway_id)
echo "API Gateway ID: $API_GATEWAY_ID"

# Test REST endpoint
curl -X POST https://${API_GATEWAY_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is my infrastructure status?"
  }' | jq '.'
```

### Step 5.2: Verify Bedrock Nova Pro Access

```bash
# List available Nova Pro models
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'nova')].[modelId,modelName]" \
  --output table

# Test Bedrock invocation
aws bedrock-runtime invoke-model \
  --model-id "us.amazon.nova-pro-1:0" \
  --content-type "application/json" \
  --accept "application/json" \
  --body '{"prompt":"Analyze these metrics: CPU 85%, Memory 72%, Disk 45%"}' \
  /tmp/bedrock-response.json

cat /tmp/bedrock-response.json | python3 -m json.tool
```

### Step 5.3: Test S3 Metric Log Reading

```bash
# Check S3 bucket for metric logs (saved every 2 hours by SRE Agent)
S3_BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 ls "s3://${S3_BUCKET}/metrics/" --recursive

# Download and review recent metrics
aws s3 cp "s3://${S3_BUCKET}/metrics/latest-metrics.json" /tmp/metrics.json
cat /tmp/metrics.json | jq '.'

# Expected format with percentages:
# {
#   "timestamp": "2024-01-15T10:00:00Z",
#   "metrics": {
#     "cpu_percent": 85.5,
#     "memory_percent": 72.3,
#     "disk_percent": 45.2
#   },
#   "instance_id": "i-0123456789abcdef0"
# }
```

### Step 5.4: Test AI Chatbot with API Gateway

```bash
# Test 1: Query infrastructure metrics
curl -X POST https://${API_GATEWAY_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze current infrastructure metrics",
    "include_metrics": true
  }' | jq '.' > /tmp/api-response.json

cat /tmp/api-response.json

# Test 2: Query specific error metrics
curl -X POST https://${API_GATEWAY_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What errors did we have in the last 2 hours?"
  }' | jq '.message'

# Expected response includes metrics extraction:
# "Based on the latest metrics (CPU: 85%, Memory: 72%, Disk: 45%), 
#  no critical errors detected. System performing normally."
```

### Step 5.5: Verify Lambda Execution

```bash
# Check AI Chatbot Lambda function
aws lambda get-function-concurrency \
  --function-name "sre-automation-ai-chatbot" \
  --query 'ReservedConcurrentExecutions'

# Monitor CloudWatch logs for chatbot
aws logs tail /aws/lambda/sre-automation-ai-chatbot --follow
```

## Monitoring & Validation

### Check Lambda Logs

```bash
# SRE Agent
aws logs tail /aws/lambda/sre-automation-sre-agent --follow

# AI Chatbot
aws logs tail /aws/lambda/sre-automation-ai-chatbot --follow
```

### Monitor Metrics

```bash
# Check recent metric data points
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$ec2_instance \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### View SNS Notifications

```bash
# Subscribe to topic for email notifications
aws sns subscribe \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --protocol email \
  --notification-endpoint your-email@example.com

# Check via console or CLI
aws sns get-topic-attributes \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --attribute-names Subscriptions
```

## Cleanup (Destroy Infrastructure)

⚠️ **WARNING**: This will delete all resources!

```bash
# First, disable termination protection if set
aws ec2 modify-instance-attribute \
  --instance-id $ec2_instance \
  --no-disable-api-termination

# Destroy Terraform resources
cd terraform
terraform destroy -var-file="envs/dev.tfvars"

# Confirm deletion
terraform show | grep "resource"
```

## Troubleshooting

### Lambda Won't Start

```bash
# Check IAM role
aws iam get-role --role-name sre-automation-lambda-execution-role

# Check policies attached
aws iam list-attached-role-policies \
  --role-name sre-automation-lambda-execution-role
```

### No CloudWatch Metrics

```bash
# Check if agent is running on EC2
aws ssm start-session --target $ec2_instance

# Inside EC2:
systemctl status amazon-cloudwatch-agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s
```

### S3 Access Denied

```bash
# Verify bucket policy
aws s3api get-bucket-policy --bucket $(terraform output -raw s3_bucket_name)

# Check Lambda IAM permissions
aws iam get-role-policy \
  --role-name sre-automation-lambda-execution-role \
  --policy-name sre-automation-lambda-s3-policy
```

### Bedrock Model Not Available

```bash
# Check available models
aws bedrock list-foundation-models --region us-west-2

# Update region in Lambda environment
aws lambda update-function-configuration \
  --function-name sre-automation-ai-chatbot \
  --environment "Variables={BEDROCK_REGION=us-west-2}"
```

## Cost Optimization

For minimal AWS lab usage:

1. **Use t3.micro for EC2**: Free tier eligible
2. **Set Lambda memory to 512MB**: Reduces execution time
3. **CloudWatch retention: 7 days**: Reduces storage costs
4. **S3 lifecycle: Archive after 30 days**: Cheaper storage
5. **DynamoDB On-Demand**: No minimum costs

Estimated monthly cost (minimal usage):
- EC2: $0-5 (or free with free tier)
- Lambda: $0-1
- S3: $0
- CloudWatch: $0-1
- DynamoDB: $0-1
- **Total: < $10/month or mostly free**

## Next Steps

1. **Customize thresholds**: Adjust CPU/disk thresholds in `variables.tf`
2. **Add more instances**: Scale the solution to multiple EC2 instances
3. **Production hardening**: Use private subnets, add VPN access
4. **Cost tracking**: Enable AWS Cost Explorer and set budgets
5. **Advanced analytics**: Add QuickSight dashboards
6. **Multi-region**: Replicate setup to other AWS regions

## Support & Documentation

- Terraform docs: See `terraform/README.md`
- Lambda functions: See `lambda/*/README.md`
- Scripts: See `scripts/`
- Demo guide: See `docs/demo-script.md`
