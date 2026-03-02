# SNS Topic for notifications
resource "aws_sns_topic" "notifications" {
  name            = "${var.project_name}-notifications"
  display_name    = "SRE Automation Notifications"
  kms_master_key_id = "alias/aws/sns"

  tags = {
    Name = "${var.project_name}-notifications"
  }
}

# SNS Email Subscription
resource "aws_sns_topic_subscription" "email" {
  count             = var.email_endpoint != "" ? 1 : 0
  topic_arn         = aws_sns_topic.notifications.arn
  protocol          = "email"
  endpoint          = var.email_endpoint
  filter_policy     = jsonencode({
    notification_type = ["resize-recommendation", "error", "alert"]
  })
}

# Topic policy to allow Lambda and CloudWatch to publish
resource "aws_sns_topic_policy" "notifications" {
  arn = aws_sns_topic.notifications.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "cloudwatch.amazonaws.com"
          ]
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.notifications.arn
      }
    ]
  })
}
