# API Gateway for AI Chatbot
resource "aws_apigatewayv2_api" "main" {
  name              = "sre-automation-api"
  protocol_type     = "HTTP"
  target            = aws_lambda_function.api_handler.arn
  cors_configuration {
    allow_credentials = false
    allow_headers     = ["content-type", "authorization"]
    allow_methods     = ["POST", "GET", "OPTIONS"]
    allow_origins     = ["*"]
    max_age           = 300
  }

  tags = {
    Name        = "sre-automation-api"
    Environment = var.environment
  }
}

# Lambda for API handler
resource "aws_lambda_function" "api_handler" {
  filename            = data.archive_file.api_handler_zip.output_path
  function_name       = "sre-automation-api-handler"
  role                = var.lambda_role_arn
  handler             = "handler.lambda_handler"
  runtime             = "python3.11"
  timeout             = 30
  memory_size         = 512
  source_code_hash    = data.archive_file.api_handler_zip.output_base64sha256

  environment {
    variables = {
      CHATBOT_FUNCTION_NAME = var.chatbot_function_name
      ALLOWED_ORIGINS       = "*"
    }
  }

  tags = {
    Name        = "sre-automation-api-handler"
    Environment = var.environment
  }
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# API stage
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integration.latency"
    })
  }

  tags = {
    Name        = "sre-automation-api-stage"
    Environment = var.environment
  }
}

# CloudWatch Logs for API
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/sre-automation"
  retention_in_days = 7

  tags = {
    Name        = "sre-automation-api-logs"
    Environment = var.environment
  }
}

# Archive Python code for Lambda
data "archive_file" "api_handler_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda_function.zip"
}
