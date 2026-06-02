output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = aws_eks_cluster.hecate.name
}

output "cluster_endpoint" {
  description = "Endpoint URL for the EKS cluster API"
  value       = aws_eks_cluster.hecate.endpoint
}

output "cluster_ca_certificate" {
  description = "Base64-encoded CA certificate for the EKS cluster"
  value       = aws_eks_cluster.hecate.certificate_authority[0].data
  sensitive   = true
}

output "cluster_version" {
  description = "Kubernetes version of the EKS cluster"
  value       = aws_eks_cluster.hecate.version
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC identity provider (for IRSA)"
  value       = aws_iam_openid_connect_provider.hecate.arn
}

output "oidc_provider_url" {
  description = "URL of the OIDC identity provider"
  value       = aws_iam_openid_connect_provider.hecate.url
}

output "node_group_role_arn" {
  description = "IAM role ARN for EKS node groups"
  value       = aws_iam_role.eks_node_group.arn
}
