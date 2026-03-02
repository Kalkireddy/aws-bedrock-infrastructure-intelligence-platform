# EC2 Instance with monitoring enabled
resource "aws_instance" "main" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id
  vpc_security_group_ids = [var.security_group]
  
  # Enable detailed CloudWatch monitoring
  monitoring = true
  
  # User data to start a sample application
  user_data_base64 = base64encode(templatefile("${path.module}/user_data.sh", {
    LOG_GROUP = "/aws/ec2/${var.project_name}"
  }))

  # Enable EBS optimization for better performance
  ebs_optimized = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 50
    delete_on_termination = true
    encrypted             = true
  }

  tags = {
    Name = "${var.project_name}-instance"
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  depends_on = [var.security_group]
}

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# CloudWatch agent configuration for EC2
resource "aws_cloudwatch_log_group" "ec2" {
  name              = "/aws/ec2/${var.project_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-ec2-logs"
  }
}

# EventBridge rule to trigger metric push from EC2
resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Alert when CPU exceeds 75%"
  alarm_actions       = []

  dimensions = {
    InstanceId = aws_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "disk_utilization" {
  alarm_name          = "${var.project_name}-disk-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DiskSpaceUsed"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when disk space exceeds 80%"
  alarm_actions       = []

  dimensions = {
    InstanceId = aws_instance.main.id
  }
}
