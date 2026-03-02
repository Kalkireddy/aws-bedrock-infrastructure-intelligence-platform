output "lambda_execution_role_arn" {
  value = aws_iam_role.lambda_execution.arn
}

output "ec2_instance_profile_name" {
  value = aws_iam_instance_profile.ec2_cloudwatch.name
}

output "ec2_automation_role_arn" {
  value = aws_iam_role.ec2_automation.arn
}
