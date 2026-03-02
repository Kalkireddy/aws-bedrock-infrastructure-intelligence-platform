output "cpu_alarm_name" {
  value = aws_cloudwatch_metric_alarm.cpu_high.alarm_name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.main.name
}

output "dashboard_name" {
  value = aws_cloudwatch_dashboard.main.dashboard_name
}
