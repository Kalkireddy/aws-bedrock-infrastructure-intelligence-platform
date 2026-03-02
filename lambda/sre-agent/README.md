# SRE Agent Lambda Function

This Lambda function monitors EC2 instances for resource utilization and recommends/performs scaling operations.

## Features

- **Metric Monitoring**: Tracks CPU and disk utilization
- **Predictive Forecasting**: Uses linear regression to forecast future trends
- **Intelligent Scaling**: Recommends EC2 instance type upgrades based on forecasts
- **Approval Workflow**: Manual approval via AWS Systems Manager Parameter Store
- **Notification System**: Sends SNS notifications with resize recommendations
- **DynamoDB Tracking**: Stores all resize requests and approval status

## Environment Variables

- `SNS_TOPIC_ARN`: ARN of SNS topic for notifications
- `PARAMETER_STORE_PREFIX`: Prefix for Parameter Store approvals (default: `/sre/dev`)
- `DYNAMODB_TABLE`: DynamoDB table for resize requests
- `LOG_LEVEL`: Logging level (default: INFO)

## Workflow

1. Lambda triggers periodically (via EventBridge CloudWatch Events)
2. Gets all running EC2 instances
3. Fetches last 24 hours of CPU and Disk metrics from CloudWatch
4. Performs trend analysis and forecasting
5. If thresholds will be breached, creates a resize request
6. Checks Parameter Store for manual approval
7. Sends SNS notification with details and approval status
8. On approval, actual resize is handled by maintenance window Lambda

## Forecasting Algorithm

Uses simple linear regression:
- Calculates average rate of change over past 24 hours
- Projects current trend 2 hours into the future
- Recommends resize if current OR forecasted value exceeds 85-90% of threshold

## Scaling Logic

- **CPU Threshold**: 75% (adjustable)
- **Disk Threshold**: 80% (adjustable)
- **Scale Action**: Always scale UP for demo (can be bidirectional in production)
- **Only scale in maintenance window**: 2 AM UTC daily
