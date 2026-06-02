output "redis_endpoint" {
  description = "Primary endpoint address of the Redis replication group"
  value       = aws_elasticache_replication_group.hecate.primary_endpoint_address
  sensitive   = true
}

output "redis_reader_endpoint" {
  description = "Reader endpoint address for Redis read replicas"
  value       = aws_elasticache_replication_group.hecate.reader_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Port on which Redis is listening"
  value       = aws_elasticache_replication_group.hecate.port
}

output "redis_sg_id" {
  description = "Security group ID for the Redis cluster"
  value       = aws_security_group.redis.id
}

output "replication_group_id" {
  description = "Identifier of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.hecate.id
}
