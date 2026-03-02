variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "sre-automation"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "min_cpu_threshold" {
  description = "Minimum CPU utilization threshold for resize"
  type        = number
  default     = 75
}

variable "enable_bedrock" {
  description = "Enable Bedrock for AI chatbot"
  type        = bool
  default     = true
}

variable "email_notifications" {
  description = "Email for resize notifications"
  type        = string
  default     = ""
}

variable "sns_email" {
  description = "Email address for SNS notifications"
  type        = string
  default     = ""
}

variable "dynamodb_read_capacity" {
  description = "DynamoDB read capacity units"
  type        = number
  default     = 5
}

variable "dynamodb_write_capacity" {
  description = "DynamoDB write capacity units"
  type        = number
  default     = 5
}
