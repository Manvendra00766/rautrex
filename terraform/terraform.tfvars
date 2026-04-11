project         = "rautrex"
env             = "prod"
aws_region      = "us-east-1"
vpc_cidr        = "10.40.0.0/16"
api_image       = "123456789012.dkr.ecr.us-east-1.amazonaws.com/rautrex-api:latest"
frontend_domain = "app.rautrex.com"
api_domain      = "api.rautrex.com"
allowed_cors_origins = [
  "https://app.rautrex.com"
]

