# Maintenance Window Lambda

Executes approved EC2 instance resizing during maintenance window.

## Workflow

1. Triggered by EventBridge at maintenance window time (2 AM UTC)
2. Queries DynamoDB for all approved resize requests
3. For each approved request:
   - Stops the instance
   - Changes instance type to next larger size
   - Starts the instance
   - Updates DynamoDB with completion status
   - Sends SNS notification

## Instance Type Upgrade Path

Demo uses simple linear upgrade path (only scale UP):
- t3.micro → t3.small
- t3.small → t3.medium
- t3.medium → t3.large
- ... and so on

In production, could use more sophisticated logic based on:
- Cost optimization
- Performance requirements
- Workload patterns
