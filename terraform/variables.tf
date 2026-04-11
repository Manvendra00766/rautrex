variable "project" {
  type    = string
  default = "rautrex"
}

variable "env" {
  type    = string
  default = "prod"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "api_image" {
  type        = string
  description = "ECR image URI for FastAPI container"
}

variable "frontend_domain" {
  type    = string
  default = "app.rautrex.com"
}

variable "api_domain" {
  type    = string
  default = "api.rautrex.com"
}

variable "allowed_cors_origins" {
  type    = list(string)
  default = ["https://app.rautrex.com"]
}

