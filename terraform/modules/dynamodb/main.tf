# DynamoDB Table for resize requests
resource "aws_dynamodb_table" "resize_requests" {
  name             = "${var.project_name}-resize-requests"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "instance_id"
  range_key        = "timestamp"

  attribute {
    name = "instance_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-resize-requests"
  }
}

# DynamoDB Table for approval workflow
resource "aws_dynamodb_table" "approvals" {
  name             = "${var.project_name}-approvals"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "request_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-approvals"
  }
}

# DynamoDB Table for AI chatbot cache
resource "aws_dynamodb_table" "chatbot_cache" {
  name             = "${var.project_name}-chatbot-cache"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "query_hash"

  attribute {
    name = "query_hash"
    type = "S"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-chatbot-cache"
  }
}
