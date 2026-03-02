# Main configuration file for SRE Automation Infrastructure

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = var.environment
}

# EC2 Module
module "ec2" {
  source = "./modules/ec2"

  project_name   = var.project_name
  instance_type  = var.instance_type
  subnet_id      = module.vpc.private_subnet_id
  security_group = module.ec2_security_group.single_security_group_id
  environment    = var.environment
  depends_on     = [module.vpc]
}

# Security Group for EC2
module "ec2_security_group" {
  source = "./modules/security_group"

  project_name = var.project_name
  vpc_id       = module.vpc.vpc_id
  environment  = var.environment
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  s3_bucket    = module.s3.bucket_name
}

# CloudWatch Module
module "cloudwatch" {
  source = "./modules/cloudwatch"

  project_name        = var.project_name
  environment         = var.environment
  min_cpu_threshold   = var.min_cpu_threshold
  sns_topic_arn       = module.sns.topic_arn
  dynamodb_table_name = module.dynamodb.resize_requests_table
}

# SNS Module
module "sns" {
  source = "./modules/sns"

  project_name   = var.project_name
  environment    = var.environment
  email_endpoint = var.sns_email
}

# Lambda Module - SRE Agent
module "lambda_sre_agent" {
  source = "./modules/lambda"

  function_name = "${var.project_name}-sre-agent"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  source_dir    = "../lambda/sre-agent"
  iam_role_arn  = module.iam.lambda_execution_role_arn
  environment_variables = {
    SNS_TOPIC_ARN          = module.sns.topic_arn
    PARAMETER_STORE_PREFIX = "/sre/${var.environment}"
    LOG_LEVEL              = "INFO"
    S3_BUCKET_NAME         = module.s3.bucket_name
  }
  timeout     = 300
  memory_size = 512
  environment = var.environment
}

# Lambda Module - AI Chatbot
module "lambda_ai_chatbot" {
  source = "./modules/lambda"

  function_name = "${var.project_name}-ai-chatbot"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  source_dir    = "../lambda/ai-chatbot"
  iam_role_arn  = module.iam.lambda_execution_role_arn
  environment_variables = {
    S3_BUCKET_NAME = module.s3.bucket_name
    BEDROCK_REGION = var.aws_region
    LOG_LEVEL      = "INFO"
  }
  timeout     = 300
  memory_size = 1024
  environment = var.environment
}

# DynamoDB Module - Resize Requests Table
module "dynamodb" {
  source = "./modules/dynamodb"

  project_name   = var.project_name
  environment    = var.environment
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
}

# API Gateway Module - Interactive AI Chatbot
module "api_gateway" {
  source = "./modules/api_gateway"

  environment            = var.environment
  lambda_role_arn        = module.iam.lambda_execution_role_arn
  chatbot_function_name  = module.lambda_ai_chatbot.lambda_function_name
  aws_region             = var.aws_region
}

# EventBridge Rule for Scheduled Maintenance Window
resource "aws_cloudwatch_event_rule" "maintenance_window" {
  name                = "${var.project_name}-maintenance-window"
  description         = "Trigger EC2 resize during maintenance window"
  schedule_expression = "cron(0 2 * * ? *)" # 2 AM UTC daily

  tags = {
    Name = "${var.project_name}-maintenance-window"
  }
}

resource "aws_cloudwatch_event_target" "maintenance_window" {
  rule      = aws_cloudwatch_event_rule.maintenance_window.name
  target_id = "${var.project_name}-resize-lambda"
  arn       = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-resize-executor"
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
