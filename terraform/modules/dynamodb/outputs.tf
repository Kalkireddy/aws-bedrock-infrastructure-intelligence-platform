output "resize_requests_table" {
  value = aws_dynamodb_table.resize_requests.name
}

output "approvals_table" {
  value = aws_dynamodb_table.approvals.name
}

output "chatbot_cache_table" {
  value = aws_dynamodb_table.chatbot_cache.name
}
