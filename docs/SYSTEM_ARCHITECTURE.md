# SRE Automation & AI Chatbot - System Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS INFRASTRUCTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐                                                  │
│  │   EC2 Instance      │                                           │
│  │  • Sample App       │ ──┐                                       │
│  │  • CloudWatch Logs  │   │                                       │
│  │  • Custom Metrics   │   │                                       │
│  └──────────────┘      │   │                                       │
│                        │   │                                       │
│                        │   ▼                                       │
│               ┌──────────────────────────┐                         │
│               │   CloudWatch            │                         │
│               │  • Metrics              │                         │
│               │  • Logs                 │                         │
│               │  • Alarms               │                         │
│               │  • Dashboard            │                         │
│               └──────────────────────────┘                         │
│                   ▲              │                                 │
│                   │              │                                 │
│          ┌────────┘              ▼                                 │
│          │          ┌────────────────────┐                         │
│          │          │   EventBridge      │                         │
│          │          │  • Scheduled Rules │                         │
│          │          │  • 2 AM UTC        │                         │
│          │          └────────────────────┘                         │
│          │                     │                                   │
│  ┌───────┴──────────┐          │                                   │
│  │                  │          │                                   │
│  ▼                  ▼          ▼                                   │
│ ┌────────────────┐ ┌──────────────────────┐                       │
│ │  SRE Agent     │ │ Maintenance Window   │                       │
│ │  Lambda        │ │ Lambda (Executor)    │                       │
│ │                │ │                      │                       │
│ │  • Analyze     │ │  • Stops EC2         │                       │
│ │    metrics     │ │  • Changes type      │                       │
│ │  • Forecast    │ │  • Starts EC2        │                       │
│ │    trends      │ │  • Updates status    │                       │
│ │  • Create      │ │                      │                       │
│ │    requests    │ └──────────────────────┘                       │
│ │  • Send alerts │           ▲                                    │
│ └────────────────┘           │                                    │
│        │                    ┌─┴─────────┐                         │
│        │                    │           │                         │
│        ▼                    ▼           ▼                         │
│  ┌──────────────────┐ ┌─────────────────────────┐                │
│  │  Parameter Store │ │  DynamoDB Tables        │                │
│  │  (Approvals)     │ │  • Resize Requests      │                │
│  │  • Approve/Deny  │ │  • Approvals            │                │
│  │    actions       │ │  • Chatbot Cache        │                │
│  └──────────────────┘ └─────────────────────────┘                │
│        ▲                        ▲                                 │
│        │                        │                                │
│        └────────┬───────────────┘                                │
│                 │                                                │
│        ┌────────▼────────┐                                       │
│        │   SNS Topic     │                                       │
│        │  • Resize       │                                       │
│        │  • Alerts       │                                       │
│        │  • Completion   │                                       │
│        └────────┬────────┘                                       │
│                 │                                                │
│                 ▼                                                │
│          📧 Email Notifications                                 │
│          👤 Engineering Team                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────────┤
│                           LOGS & AI                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐        ┌──────────────────┐                      │
│  │  CloudWatch  │        │   S3 Bucket      │                      │
│  │  Logs        │───────▶│   (Historical     │                      │
│  │              │        │    Logs)          │                      │
│  └──────────────┘        └──────────────────┘                      │
│          │                        │                                │
│          │                        │                                │
│          └────────────┬───────────┘                                │
│                       │                                            │
│                       ▼                                            │
│          ┌──────────────────────────────┐                          │
│          │   AI Chatbot Lambda          │                          │
│          │  (Using Bedrock)             │                          │
│          │                              │                          │
│          │  • Fetch logs                │                          │
│          │  • Analyze patterns          │                          │
│          │  • Answer questions          │                          │
│          │  • Detect anomalies          │                          │
│          │  • Cache responses           │                          │
│          └──────────┬───────────────────┘                          │
│                     │                                              │
│                     ▼                                              │
│          ┌──────────────────────────────┐                          │
│          │   Amazon Bedrock             │                          │
│          │   (AWS Nova Pro)             │                          │
│          │                              │                          │
│          │  • Log analysis              │                          │
│          │  • NLP understanding         │                          │
│          │  • Recommendations           │                          │
│          └──────────┬───────────────────┘                          │
│                     │                                              │
│                     ▼                                              │
│            API Gateway / CLI                                   │
│            (Query Interface)                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    GITLAB CI/CD PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Define → Validate → Plan → Approve → Apply → Deploy             │
│   Code    Syntax    IaC    Manual    Full     Infrastructure      │
│                            Gate      Infra                         │
│                                                                     │
│  Branch: main/develop                                            │
│  Trigger: Merge Request → gitlab-ci.yml                          │
│  Stages: validate, plan, apply                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. EC2 Monitoring Layer

**Components:**
- EC2 Instance (t3.micro → t3.2xlarge scalable)
- CloudWatch Agent (installed via user data)
- Security Groups (SSH, HTTP, HTTPS)
- IAM Instance Profile

**Metrics Collected:**
- CPU Utilization (AWS/EC2 namespace)
- Memory Usage (SREAutomation namespace)
- Disk Space (SREAutomation namespace)
- Application Logs

**Data Flow:**
```
EC2 Instance
    ↓
CloudWatch Agent (polls every 60s)
    ↓
CloudWatch Metrics + Logs
    ↓
Stored (7-day retention)
    ↓
Available for SRE Agent & AI Chatbot
```

### 2. SRE Agent - Predictive Scaling

**Workflow:**

```
EventBridge (Every 2 Hours)
    ↓
SRE Agent Lambda
    ├─ Get all EC2 instances
    ├─ Fetch last 24h metrics from CloudWatch
    ├─ Analyze CPU, Memory & Disk trends
    ├─ Generate realistic sample metrics
    ├─ Forecast 2 hours ahead (linear regression)
    ├─ Compare forecast vs threshold
    ├─ Save metrics to S3 (formatted logs)
    │  └─ Format:
    │     • CPU Usage: Current/Average/Peak %
    │     • Memory Usage: Current/Average/Peak %
    │     • Disk Usage: Current/Average/Peak %
    ├─ Create DynamoDB resize request (if needed)
    ├─ Send SNS notification
    └─ Check Parameter Store for approval status
         ↓
    Store status in DynamoDB
         ↓
    SNS → Email to engineers
```

**Forecasting Algorithm:**

```python
# Simple linear regression
changes = [values[i+1] - values[i] for i in range(len(values))]
avg_change = sum(changes) / len(changes)
current = values[-1]
forecasted = current + (avg_change * forecast_periods)

# Recommendation:
if forecasted >= threshold or current >= (threshold * 0.85):
    recommend_resize()
```

**Scale Decision Matrix:**

| Metric | Current | Forecast | Action |
|--------|---------|----------|--------|
| CPU | <50% | <50% | None |
| CPU | 50-75% | <75% | Monitor |
| CPU | 50-75% | >75% | Recommend |
| CPU | >75% | Any | Recommend |
| Disk | Similar logic as CPU | | |

### 3. Maintenance Window - Resize Executor

**Scheduled Execution:**
- CloudWatch Event Rule: `0 2 * * ? *` (2 AM UTC daily)
- Triggers: Maintenance Window Lambda
- Scope: Approved resize requests only

**Resize Process:**

```
Maintenance Window Triggered (2 AM UTC)
    ↓
Query DynamoDB for approved requests
    ↓
For each approved request:
    ├─ Get current instance type
    ├─ Look up target type (next size up)
    ├─ Stop instance (graceful shutdown)
    ├─ Wait until stopped
    ├─ Modify instance type
    ├─ Start instance
    ├─ Wait until running
    ├─ Update DynamoDB status → "completed"
    └─ Send SNS notification
         ↓
    Return results to SNS subscribers
```

**Instance Type Upgrade Path (Demo):**

```
t3.micro     (0.5 GB RAM)
    ↓ (scale up)
t3.small     (2 GB RAM)
    ↓ (scale up)
t3.medium    (4 GB RAM)
    ↓ (scale up)
t3.large     (8 GB RAM)
    ↓ (scale up)
t3.xlarge    (16 GB RAM)
    ↓ (scale up)
t3.2xlarge   (32 GB RAM)
```

In production, can include:
- Cost optimization
- Performance tiers
- Application requirements
- Reserved capacity planning

### 4. AI Chatbot - Intelligent Log Analysis

**Capabilities:**

#### Rule-Based Analysis (Fast, No AI Cost)
```
Query → Pattern Matching → Rules Engine → Response

Examples:
  "What errors?" → Regex /ERROR|EXCEPTION/ → Extract errors
  "Query by user?" → Pattern match + user filter → Return queries
  "Error trending?" → Calculate error ratio → Trend detection
  "Anomalies?" → Multiple patterns → Aggregated alerts
```

#### AI-Powered Analysis (Bedrock + Cache)
```
Query
    ↓
Check DynamoDB cache (MD5 hash of query)
    ├─ Cache hit → Return cached response
    └─ Cache miss → Continue
         ↓
    Fetch metric logs from S3 (saved by SRE Agent)
         ↓
    Extract metrics: CPU/Memory/Disk percentages
         ↓
    Prepare prompt for AWS Nova Pro with metrics
         ↓
    Invoke Amazon Bedrock (aws.nova-pro)
         ↓
    Get response with metrics & insights
         ↓
    Cache result for 24 hours
         ↓
    Return to user via API Gateway (REST)
```

**Bedrock Model Details:**
- Model: AWS Nova Pro (latest stable)
- Context window: 200K tokens
- Max output: 4096 tokens
- Latency: ~2-5 seconds
- Cost: ~$0.30/$1.20 per million tokens (90% cheaper than Claude)

**Log Patterns Detected:**

```
Errors:
  - ERROR, EXCEPTION, FAILED, FATAL
  - Connection refused, timeout
  - Out of memory (OOM)
  - Deadlock detected
  
Queries (Database):
  - SELECT, INSERT, UPDATE, DELETE
  - Extracted with username
  - Duration analysis
  
Warnings:
  - Long running queries
  - High resource usage
  - Performance degradation
  
Anomalies:
  - Error rate > 5%
  - Multiple timeouts
  - Connection pool exhaustion
  - Disk space critical
```

### 5. GitLab CI/CD Pipeline

**Pipeline Stages:**

```
Commit/MR created
    ↓
┌───────────────────────────────────┐
│ 1. VALIDATE                       │
│ ├─ terraform validate             │
│ ├─ terraform fmt -check           │
│ └─ Syntax checks                  │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ 2. PLAN (dev/prod)                │
│ ├─ terraform init                 │
│ ├─ terraform plan                 │
│ └─ Output: tfplan.dev/prod        │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ 3. APPLY (Manual Approval)        │
│ ├─ Review plan changes            │
│ ├─ Approval gate (MANUAL)         │
│ ├─ terraform apply                │
│ └─ Update live infrastructure     │
└───────────────────────────────────┘
    ↓
Infrastructure live on AWS
```

**Branch Strategy:**
- `main` → Production deployment (manual approval)
- `develop` → Development/staging (manual approval)
- `feature/*` → Feature branches (validate only)

### 6. Data Storage & Persistence

**DynamoDB Tables:**

| Table | Primary Key | Attributes | TTL | Purpose |
|-------|------------|-----------|-----|---------|
| `resize-requests` | instance_id, timestamp | metrics, forecast, status | 7 days | Track resize recommendations & history |
| `approvals` | request_id | approved_by, approved_at, comment | 30 days | Audit trail of approvals |
| `chatbot-cache` | query_hash | query, response, timestamp | 24 hours | Cache AI responses |

**S3 Buckets:**

| Bucket | Purpose | Lifecycle |
|--------|---------|-----------|
| `sre-automation-logs-{acct}` | Log storage, Terraform state | Archive after 30d → Glacier after 90d |

**CloudWatch:**

| Resource | Retention | Purpose |
|----------|-----------|---------|
| `/aws/ec2/{project}` | 7 days | EC2 system logs |
| `/aws/lambda/{function}` | 7 days | Lambda execution logs |
| `SREAutomation` namespace | N/A | Custom metrics |

## Data Flow Diagrams

### Scenario 1: EC2 CPU Spike Detection

```
11:00 UTC: CPU starts increasing
   ↓
11:05 UTC: CloudWatch records 45% CPU
11:10 UTC: CloudWatch records 55% CPU
11:15 UTC: CloudWatch records 65% CPU
   ↓
12:00 UTC: SRE Agent runs (every 2 hours)
   ├─ Fetches last 24h data
   ├─ Generates realistic metrics
   ├─ Saves metrics to S3 (CPU/Memory/Disk %s)
   ├─ Calculates: avg_change = +0.5% per 5-min
   ├─ Current: 65%
   ├─ Forecast (2h ahead): 65 + (0.5 * 24) = 77%
   ├─ Threshold: 75%
   ├─ Result: 77% > 75% → RECOMMEND RESIZE
   ├─ Create DynamoDB request
   ├─ Send SNS notification
   └─ Check approval status (none yet)
   ↓
12:30 UTC: Engineer reviews & approves via CLI
   ├─ Sets Parameter Store: resize-approved = true
   └─ Updates DynamoDB: approval_status = true
   ↓
14:00 UTC: SRE Agent runs again (next 2h cycle)
   ├─ Detector: CPU now 75%+ or forecast still high
   └─ Status: resize still approved
   ↓
02:00 UTC: Maintenance Window triggered (EventBridge daily)
   ├─ Queries approved requests
   ├─ Finds t3.micro instance needing upgrade
   ├─ Stops instance (30 sec)
   ├─ Modifies type to t3.small
   ├─ Starts instance (30 sec)
   ├─ Saves completion metrics to S3
   ├─ Updates DynamoDB
   └─ Sends completion notification
   ↓
02:05 UTC: Instance up, new type shows in dashboard
   ├─ CPU immediately drops to 30%
   └─ Forecast validated! ✓
```

### Scenario 2: Error Rate Spike + Metrics Extraction

```
Database query timeout occurs
   ↓
Application logs: "ERROR: Query timeout - 5000ms"
   ↓
CloudWatch Logs receives entry
   ↓
SRE Agent (every 2h) saves metrics to S3:
   ├─ CPU Usage: Current 65%, Average 58%, Peak 72%
   ├─ Memory Usage: Current 78%, Average 72%, Peak 91%
   └─ Disk Usage: Current 42%, Average 38%, Peak 55%
   ↓
AI Chatbot triggered with query via API Gateway:
   "What errors occurred and what are the metrics?"
   ↓
Chatbot execution:
├─ Check cache (miss)
├─ Fetch S3 metric logs (latest from SRE Agent)
├─ Extract metrics with clear percentages
│  ├─ CPU: Current 65%, Average 58%, Peak 72%
│  ├─ Memory: Current 78%, Average 72%, Peak 91%
│  └─ Disk: Current 42%, Average 38%, Peak 55%
├─ Fetch CloudWatch logs for errors (1h)
├─ Local pattern matching:
│  └─ Find 15 ERROR entries
│  └─ Parse: 3 timeouts, 2 connections, 10 others
├─ Send metrics + logs to Bedrock with context
├─ AWS Nova Pro analyzes and provides:
│  ├─ Error summary with causes
│  ├─ Metric analysis: HIGH memory (91% peak!)
│  ├─ Pattern identification
│  ├─ Correlation: Memory pressure → timeouts
│  └─ Recommendations
├─ Cache response (24h TTL)
└─ Return via API Gateway (REST)
   ↓
Chatbot response:
```
{
  "timestamp": "2026-03-01T10:00:00Z",
  "error_count": 15,
  "error_rate": "3.5%",
  "top_issues": [
    "Query timeouts (20%)",
    "Connection pool exhaustion (13%)",
    "Permission errors (67%)"
  ],
  "metrics_extracted": {
    "cpu": {"current": "65%", "average": "58%", "peak": "72%"},
    "memory": {"current": "78%", "average": "72%", "peak": "91%"},
    "disk": {"current": "42%", "average": "38%", "peak": "55%"}
  },
  "analysis": "High memory usage (peak 91%) correlating with query timeouts. 
              Recommend: Check connection pool config, optimize queries, 
              or increase instance memory.",
  "recommendation": "Scale up to t3.small (2GB → 4GB RAM) to handle 
                    concurrent connections better"
}
```

## Scalability & Performance

### Horizontal Scaling

**EC2 Instances:**
- Single instance in demo
- Scales to N instances: SRE Agent processes all via `describe_instances`
- DynamoDB GSI on status: Efficient queries across all instances

**Lambda Concurrency:**
- SRE Agent: Auto-scales to handle all instances
- Chatbot: Concurrent user requests handled
- Limits: 1000 concurrent executions per account (soft limit)

**CloudWatch:**
- No practical limit on metrics
- Log group size unlimited
- Query performance with proper retention

### Cost Optimization

**Compute:**
- Lambda: Pay per 100ms execution
- CloudWatch: $0.50 per 1M API calls  
- EC2: t3.micro (free tier eligible)

**Storage:**
- DynamoDB on-demand: Pay per request (no minimum)
- S3: $0.023 per GB/month (metric logs ~$0.05/month)
- CloudWatch Logs: $0.50 per GB/month (7-day retention)

**Networking:**
- Data transfer within region: Free
- NAT Gateway: $0.32/hour + data charges
- Cross-region: $0.01-0.05 per GB

**Monthly Cost Breakdown:**
```
EC2 t3.micro:           $3.50  (730 hours @ $0.0048/hr)
Lambda:                 $0.50  (60K invocations/month)
CloudWatch:             $2.00  (Logs + Metrics + Dashboard)
DynamoDB:               $1.50  (On-demand pricing)
S3 (metric logs):       $0.05  (logs from SRE Agent every 2h)
NAT Gateway:            $3.20  ($0.32/hr + minimal data)
VPC Flow Logs:          $0.10  (Minimal)
─────────────────────────────
Total:                 ~$11.50/month
Annual:                ~$138/year
```

### Bottlenecks & Mitigation

| Bottleneck | Cause | Solution |
|-----------|-------|----------|
| Lambda timeout | Slow metric queries | Add CloudWatch Logs Insights query caching |
| High Bedrock cost | Every unique query calls API | DynamoDB caching (24h TTL) |
| DynamoDB hotspots | All writes to same partition | Use GSI, add timestamps |
| S3 list latency | Large log bucket | Use S3 Inventory, prefix filtering |
| SNS subscription backlog | Too many subscribers | Use SQS with Lambda dead-letter queue |

## Security Posture

### IAM Least Privilege

**SRE Agent Lambda:**
```
✓ Can: Read CloudWatch metrics, EC2 describe, SNS publish, SSM Parameter read
✗ Can't: Modify EC2, write CloudWatch alarms, delete resources
```

**Maintenance Window Lambda:**
```
✓ Can: Stop/start EC2, modify instance attributes, write DynamoDB
✗ Can't: Terminate EC2, modify security groups, access other accounts
```

**AI Chatbot Lambda:**
```
✓ Can: Read CloudWatch Logs, S3 read, invoke Bedrock, cache to DynamoDB
✗ Can't: Delete logs, modify buckets, write to other resources
```

### Encryption

- **S3:** Server-side encryption (AES256)
- **DynamoDB:** Encryption at rest (AWS managed keys)
- **SNS:** Optional KMS encryption
- **Parameter Store:** Encryption by default
- **VPC Flow Logs:** Logging enabled

### Network Isolation

- EC2 in private subnet (no direct internet)
- NAT Gateway for outbound traffic
- VPC endpoints for AWS services (cost savings)
- Security groups: Minimal required access

## Monitoring & Observability

### CloudWatch Dashboards

**Main Dashboard Metrics:**
```
- EC2 CPU/Memory/Disk trends
- Lambda execution count & duration
- Error rate trends
- DynamoDB consumed capacity
- SNS message count
```

### Alarms

```
CPU Utilization > 75% → SNS notification → Engineer reviews
Error Rate > 5% → SNS notification → Investigate
Lambda Errors > 0 → CloudWatch Logs → Debug
DynamoDB throttling → Scale write capacity
```

### Logs

```
CloudWatch Logs Groups:
  /aws/ec2/sre-automation
  /aws/lambda/sre-automation-sre-agent
  /aws/lambda/sre-automation-ai-chatbot
  /aws/lambda/sre-automation-maintenance-window

Retention: 7 days (configurable)
Searchable via CloudWatch Logs Insights
```

---

## Architecture Evolution

**Current (Demo):**
- Single EC2 monitoring
- Synchronous AI analysis

**Next (Production):**
- Multiple EC2 fleets
- Reserved instances + Spot instances
- Auto Scaling Groups (with SRE Agent as input)
- Async job queues for long-running analyses
- Multi-AZ/Multi-region deployment

---

For implementation details, see `DEPLOYMENT_GUIDE.md`.  
For demo walkthrough, see `DEMO_SCRIPT.md`.
