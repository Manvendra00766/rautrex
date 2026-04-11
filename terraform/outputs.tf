output "cloudfront_domain" {
  value = aws_cloudfront_distribution.cdn.domain_name
}

output "api_gateway_endpoint" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "internal_alb_dns" {
  value = aws_lb.internal_api.dns_name
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

