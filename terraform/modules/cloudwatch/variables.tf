variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "min_cpu_threshold" {
  type = number
}

variable "sns_topic_arn" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}
