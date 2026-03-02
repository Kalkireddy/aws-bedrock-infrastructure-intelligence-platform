output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "s3_bucket_name" {
  description = "S3 bucket for logs and states"
  value       = module.s3.bucket_name
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2.instance_id
}

output "lambda_sre_agent_arn" {
  description = "ARN of SRE Agent Lambda"
  value       = module.lambda_sre_agent.lambda_arn
}

output "lambda_ai_chatbot_arn" {
  description = "ARN of AI Chatbot Lambda"
  value       = module.lambda_ai_chatbot.lambda_arn
}

output "sns_topic_arn" {
  description = "SNS Topic ARN for notifications"
  value       = module.sns.topic_arn
}

output "cloudwatch_alarm_cpu" {
  description = "CloudWatch Alarm for CPU threshold"
  value       = module.cloudwatch.cpu_alarm_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table for resize requests"
  value       = module.dynamodb.resize_requests_table
}

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "api_endpoint" {
  description = "API Gateway endpoint for interactive AI Chatbot"
  value       = module.api_gateway.api_endpoint
}

output "api_full_url" {
  description = "Full URL to invoke AI Chatbot via API"
  value       = "${module.api_gateway.full_api_url}/ask"
}

output "chatbot_usage_example" {
  description = "Example curl command to use the API"
  value = <<-EOT
    curl -X POST ${module.api_gateway.full_api_url}/ask \
      -H "Content-Type: application/json" \
      -d '{"question": "Why is CPU high?"}'
  EOT
}
