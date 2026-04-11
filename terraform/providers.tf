terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# CloudFront + WAF (scope CLOUDFRONT) are managed in us-east-1
provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}

