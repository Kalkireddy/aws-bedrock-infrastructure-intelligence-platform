# CloudWatch alarms for CPU and Disk
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = var.min_cpu_threshold
  alarm_description   = "Alert when CPU utilization is high"
  alarm_actions       = [var.sns_topic_arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "${var.project_name}-cpu-high"
  }
}

resource "aws_cloudwatch_metric_alarm" "disk_high" {
  alarm_name          = "${var.project_name}-disk-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DiskSpaceUsed"
  namespace           = "SREAutomation"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when disk utilization is high"
  alarm_actions       = [var.sns_topic_arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "${var.project_name}-disk-high"
  }
}

# CloudWatch Log Group for all application logs
resource "aws_cloudwatch_log_group" "main" {
  name              = "/aws/${var.project_name}/application"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-logs"
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-lambda-logs"
  }
}

# Metric filter for errors
resource "aws_cloudwatch_log_metric_filter" "errors" {
  name           = "${var.project_name}-error-filter"
  log_group_name = aws_cloudwatch_log_group.main.name
  pattern        = "[ERROR]"

  metric_transformation {
    name      = "ErrorCount"
    namespace = "SREAutomation"
    value     = "1"
  }
}

# Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", { stat = "Average" }],
            ["SREAutomation", "DiskSpaceUsed", { stat = "Average" }],
            ["SREAutomation", "ErrorCount", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "Key Metrics"
        }
      }
    ]
  })
}
