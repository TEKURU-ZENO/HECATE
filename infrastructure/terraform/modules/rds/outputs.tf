output "db_instance_id" {
  description = "Identifier of the RDS instance"
  value       = aws_db_instance.hecate.id
}

output "db_endpoint" {
  description = "Connection endpoint for the RDS instance"
  value       = aws_db_instance.hecate.endpoint
  sensitive   = true
}

output "db_port" {
  description = "Port on which the RDS instance is listening"
  value       = aws_db_instance.hecate.port
}

output "db_name" {
  description = "Name of the PostgreSQL database"
  value       = aws_db_instance.hecate.db_name
}

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret containing DB credentials"
  value       = aws_secretsmanager_secret.rds_master.arn
}

output "replica_endpoint" {
  description = "Connection endpoint for the read replica (prod only)"
  value       = length(aws_db_instance.hecate_replica) > 0 ? aws_db_instance.hecate_replica[0].endpoint : null
  sensitive   = true
}
