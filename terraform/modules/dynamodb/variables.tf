variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "read_capacity" {
  type    = number
  default = 5
}

variable "write_capacity" {
  type    = number
  default = 5
}
