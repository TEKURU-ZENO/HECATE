output "vpc_id" {
  value       = aws_vpc.hecate_vpc.id
  description = "Provisioned VPC ID"
}

output "eks_cluster_endpoint" {
  value       = aws_eks_cluster.eks.endpoint
  description = "EKS Cluster API Endpoint"
}

output "database_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "RDS Database Connection Endpoint"
}

output "kafka_bootstrap_brokers" {
  value       = aws_msk_cluster.kafka.bootstrap_brokers
  description = "Amazon MSK Kafka Connection String"
}
