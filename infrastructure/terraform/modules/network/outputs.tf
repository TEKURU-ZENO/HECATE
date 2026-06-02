output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.hecate.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.hecate.cidr_block
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.hecate[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.hecate.id
}

output "eks_control_plane_sg_id" {
  description = "Security group ID for the EKS control plane"
  value       = aws_security_group.eks_control_plane.id
}

output "rds_sg_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "msk_sg_id" {
  description = "Security group ID for MSK Kafka"
  value       = aws_security_group.msk.id
}
