# Quick Reference Card - SRE Automation Operations

## 🚀 Quick Start (Copy/Paste Commands)

### Check Infrastructure Health
```bash
# Set environment
export INSTANCE_ID="i-0c5ce251dbadfcd56"
export REGION="us-east-1"

# 1. EC2 Status
aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION \
  --query 'Reservations[0].Instances[0].[InstanceType, State.Name, LaunchTime]' --output table

# 2. CloudWatch Metrics (Last 1 Hour)
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average --region $REGION --output table

# 3. Alarm Status
aws cloudwatch describe-alarms --region $REGION \
  --query 'MetricAlarms[?contains(AlarmName, `sre-automation`)].[AlarmName, StateValue, StateReason]' --output table

# 4. Recent Resizes (DynamoDB)
aws dynamodb scan --table-name sre-automation-resize-requests \
  --expression-attribute-names '{"#ts":"timestamp", "#st":"status"}' \
  --projection-expression "#ts, #st, instance_id" \
  --scan-index-forward False --limit 5 --region $REGION --output table
```

---

## 📊 Dashboard Status at a Glance

| Component | Current Status | Threshold | Action |
|-----------|---|---|---|
| **CPU Utilization** | 8.68% | < 75% | ✅ OK |
| **Disk Utilization** | ~15% | < 80% | ✅ OK |
| **Memory** | N/A | Monitor | ✅ OK |
| **EC2 Instance** | t3.micro | Running | ✅ OK |
| **SRE Agent Lambda** | Working | Every 5 min | ✅ OK |
| **AI Chatbot Lambda** | Working | On-demand | ✅ OK |
| **CloudWatch Alarms** | 2 Active | CPU & Disk | ✅ OK |
| **SNS Topic** | Active | Monitoring | ✅ OK |
| **DynamoDB** | 3 Tables | On-demand | ✅ OK |

---

## 🔍 Troubleshooting Logic Tree

```
Issue: Alarm triggered
├─ CPU High?
│  ├─ Check current load: aws cloudwatch get-metric-statistics...
│  ├─ Expected? → OK (temporary spike)
│  └─ Trending up? → Check SRE recommendations
│
├─ Disk Full?
│  ├─ SSH into instance: aws ssm start-session --target $INSTANCE_ID
│  ├─ Check: df -h
│  ├─ Clear logs: rm -rf /var/log/old*
│  └─ Verify S3: aws s3 ls s3://sre-automation-logs-xxx
│
└─ Lambda Error?
   ├─ Check logs: aws logs tail /aws/lambda/sre-automation-sre-agent --follow
   ├─ Check IAM: aws iam get-role-policy ...
   └─ Redeploy: cd terraform && terraform apply

Issue: SRE Agent not working
├─ Check Lambda: aws lambda get-function-concurrency --function-name sre-automation-sre-agent
├─ Check Logs: aws logs tail /aws/lambda/sre-automation-sre-agent --follow
├─ Re-invoke: aws lambda invoke --function-name sre-automation-sre-agent /tmp/result.json
└─ Redeploy: terraform apply -var-file=envs/dev.tfvars

Issue: Not receiving email alerts
├─ Check subscription: aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:995429641089:sre-automation-notifications
├─ Verify email confirmed
├─ Check spam folder
├─ Re-subscribe: aws sns subscribe --topic-arn arn:aws:sns:... --protocol email --notification-endpoint your-email@example.com

Issue: Need to manually trigger resize
├─ Create approval: aws ssm put-parameter --name /sre/dev/resize-approval --value 'approved' --overwrite
├─ Trigger lambda: aws lambda invoke --function-name sre-automation-resize-lambda /tmp/result.json
└─ Monitor: aws logs tail /aws/lambda/sre-automation-resize-lambda --follow
```

---

## 🎯 Common Operations

### View Current Resize Recommendations
```bash
aws dynamodb scan --table-name sre-automation-resize-requests \
  --filter-expression "#st = :status" \
  --expression-attribute-names '{"#st":"status"}' \
  --expression-attribute-values '{":status":{"S":"pending"}}' \
  --region us-east-1 --output table
```

### Manually Trigger Resize (Emergency)
```bash
# 1. Set approval
aws ssm put-parameter \
  --name "/sre/dev/resize-approval" \
  --value "APPROVED_BY_ON_CALL" \
  --overwrite \
  --region us-east-1

# 2. Trigger Maintenance Lambda
aws lambda invoke \
  --function-name sre-automation-resize-lambda \
  --region us-east-1 \
  /tmp/resize_result.json

# 3. Monitor progress
watch -n 5 'aws logs tail /aws/lambda/sre-automation-resize-lambda --follow'
```

### Get AI Chatbot Insights
```bash
# Query: What errors in last 7 days?
PAYLOAD=$(echo -n '{"query":"What errors?","log_source":"cloudwatch"}' | base64)
aws lambda invoke \
  --function-name sre-automation-ai-chatbot \
  --payload $PAYLOAD \
  --region us-east-1 \
  /tmp/ai_analysis.json

cat /tmp/ai_analysis.json | python3 -m json.tool
```

### Change CPU Threshold
```bash
# 1. Edit config
vim terraform/envs/dev.tfvars
# Change: min_cpu_threshold = 75 → 80

# 2. Plan
terraform plan -var-file=envs/dev.tfvars -out=tfplan.new

# 3. Apply
terraform apply tfplan.new
```

### Upgrade Instance Type Size
```bash
# In maintenance window, manually:
aws ec2 modify-instance-attribute \
  --instance-id i-0c5ce251dbadfcd56 \
  --instance-type '{"Value": "t3.small"}' \
  --region us-east-1

# Must stop first:
aws ec2 stop-instances --instance-ids i-0c5ce251dbadfcd56
aws ec2 wait instance-stopped --instance-ids i-0c5ce251dbadfcd56
# [modify type]
aws ec2 start-instances --instance-ids i-0c5ce251dbadfcd56
```

---

## 📞 Emergency Contact Procedures

### 🔴 Critical (CPU > 90% or Disk > 95%)
**What to do:**
1. SSH to EC2: `aws ssm start-session --target i-0c5ce251dbadfcd56`
2. Check process: `top` or `ps aux`
3. Kill if rogue: `kill -9 PID`
4. Manually trigger resize if needed
5. Notify on-call engineer

### 🟠 High (CPU 75-90%)
**What to do:**
1. Check SRE Agent recommendation
2. Review CloudWatch dashboard
3. If approved: Wait for 2 AM UTC or trigger manually
4. Monitor progress in logs

### 🟡 Medium (CPU 50-75%)
**What to do:**
1. Note for next planning meeting
2. Monitor trend over 24 hours
3. No immediate action needed
4. Consider load balancing

### 🟢 Normal (CPU < 50%)
**What to do:**
1. Everything is working
2. Continue 24/7 monitoring
3. Review monthly cost & performance

---

## 📈 Performance Metrics to Track

```bash
# Weekly Report Script
#!/bin/bash
echo "=== Weekly SRE Report ==="
echo "Period: $(date -d '7 days ago' +%Y-%m-%d) to $(date +%Y-%m-%d)"
echo ""

# Max CPU
echo "Max CPU Utilization:"
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0c5ce251dbadfcd56 \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 --statistics Maximum \
  --query 'Datapoints[0].Maximum' --output text

# Resize count
echo "Resizes This Week:"
aws dynamodb scan --table-name sre-automation-resize-requests \
  --filter-expression "#ts >= :week" \
  --expression-attribute-names '{"#ts":"timestamp"}' \
  --expression-attribute-values '{":week":{"N":"'$(date -d '7 days ago' +%s)'000"}}' \
  --select COUNT --output text

# Alert count
echo "Alarms This Week: [Check CloudWatch Logs]"
aws logs filter-log-events \
  --log-group-name /aws/cloudwatch-alarms \
  --start-time $(date -d '7 days ago' +%s)000 \
  --query 'events | length(@)' --output text
```

---

## 📋 Weekly Checklist

- [ ] Review CloudWatch dashboard
- [ ] Check CPU/Disk trends
- [ ] Verify SNS emails being received
- [ ] Test manual resize procedure
- [ ] Review costs in AWS Billing
- [ ] Check DynamoDB table sizes
- [ ] Update runbook if needed
- [ ] Test disaster recovery (if applicable)

---

## 📚 Key Files Location

```
Terraform:
  /terraform/main.tf                    (Root config)
  /terraform/envs/dev.tfvars           (Dev config)
  /terraform/modules/                  (All services)

Lambda Code:
  /lambda/sre-agent/handler.py         (Prediction)
  /lambda/ai-chatbot/handler.py        (AI analysis)
  /lambda/maintenance-window/handler.py (Executor)

Documentation:
  /docs/SYSTEM_ARCHITECTURE.md         (Detailed)
  /docs/DEPLOYMENT_GUIDE.md            (Setup)
  /docs/DEMO_SCRIPT.md                 (Demo steps)
  /docs/CLIENT_HANDOVER_GUIDE.md       (For client)
  /docs/ARCHITECTURE_DIAGRAMS.md       (Visual)

CI/CD:
  /.gitlab-ci.yml                      (Pipeline)
  /scripts/generate-sample-logs.py     (Testing)
```

---

## 🔐 AWS Credentials & Access

```
Account ID:        995429641089
Region:            us-east-1
IAM User:          shiv-admin (admin access)
Access Method:     AWS CLI / SSO
Instance Access:   SSH via AWS Systems Manager Session Manager

Secure the following:
✓ AWS_ACCESS_KEY_ID
✓ AWS_SECRET_ACCESS_KEY
✓ Terraform state file (tfstate)
✓ Parameter Store values (/sre/dev/*)
```

---

## 💰 Expected Monthly Costs

```
EC2 t3.micro:        $3.50   (730 hours @ $0.0048/hr)
Lambda:              $0.50   (Caching reduces invocations)
CloudWatch:          $2.00   (Logs + Metrics + Dashboard)
DynamoDB:            $1.50   (On-demand pricing)
S3:                  $0.80   (Storage + transfers)
NAT Gateway:         $3.20   ($0.32/hr + data)
VPC Flow Logs:       $0.10   (Minimal data)
───────────────────────────
TOTAL:              ~$11.50/month

Budget Alert: Set to $50/month in AWS Billing
Cost Optimization: Already implemented Nova Pro, on-demand DynamoDB
```

---

## 🎓 Training Schedule

**Week 1 - Basics:**
- Day 1: Architecture overview
- Day 2: CloudWatch dashboard
- Day 3: Alarm interpretation
- Day 4: Lambda testing
- Day 5: Log analysis

**Week 2 - Operations:**
- Day 1: Manual resize procedure
- Day 2: Troubleshooting common issues
- Day 3: Escalation procedures
- Day 4: Monitoring best practices
- Day 5: Cost optimization

**Week 3 - Advanced:**
- Day 1: Custom metrics
- Day 2: Scaling strategy
- Day 3: Disaster recovery
- Day 4: Performance tuning
- Day 5: Handoff

---

## ✅ Post-Deployment Checklist

- [x] Infrastructure deployed
- [x] All services tested
- [x] Monitoring confirmed
- [x] Alarms configured
- [x] SNS working
- [x] Lambda functions verified
- [x] CloudWatch dashboard created
- [x] Documentation complete
- [x] Demo performed
- [ ] Client training completed
- [ ] Support handoff scheduled
- [ ] 30-day follow-up planned

---

## 🎯 Success Criteria

System is working when:
- ✅ EC2 instance running continuously
- ✅ CloudWatch metrics arriving every 60s
- ✅ SRE Agent running every 5 min
- ✅ Alarms trigger when thresholds exceeded
- ✅ Email alerts received
- ✅ AI Chatbot responds to queries
- ✅ Resize executes without errors
- ✅ Monthly cost < $15

---

## 📞 Support Contact

**Technical Issues:**
- Email: support@example.com
- Slack: #sre-automation-support
- Phone: +1 (XXX) XXX-XXXX
- Hours: 9 AM - 6 PM IST

**Escalation:**
- P1 (Critical): Immediate call
- P2 (High): Email + 1h response
- P3 (Medium): Email within 4h
- P4 (Low): Email within 1 day

**Remember:**
- Save this card for quick reference
- Bookmark the documentation
- Test procedures before using in production
- Keep AWS credentials secure
- Report issues immediately

---

**Last Updated:** March 1, 2026  
**System Version:** 1.0 (Production Ready)  
**Status:** ✅ All Green

