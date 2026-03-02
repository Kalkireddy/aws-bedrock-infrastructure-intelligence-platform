variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Lambda"
  type        = string
}

variable "chatbot_function_name" {
  description = "AI Chatbot Lambda function name"
  type        = string
  default     = "sre-automation-ai-chatbot"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
