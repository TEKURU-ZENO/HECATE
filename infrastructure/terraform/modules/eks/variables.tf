variable "environment" {
  description = "Deployment environment (dev/staging/prod)"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.29"
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for EKS nodes"
  type        = list(string)
}

variable "control_plane_sg_id" {
  description = "Security group ID for the EKS control plane"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for EKS secrets encryption"
  type        = string
}

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to access the EKS API endpoint (prod only)"
  type        = list(string)
  default     = []
}

variable "system_node_instance_type" {
  description = "EC2 instance type for the system node group"
  type        = string
  default     = "t3.medium"
}

variable "system_node_desired" {
  description = "Desired number of system nodes"
  type        = number
  default     = 2
}

variable "system_node_min" {
  description = "Minimum number of system nodes"
  type        = number
  default     = 1
}

variable "system_node_max" {
  description = "Maximum number of system nodes"
  type        = number
  default     = 4
}

variable "agent_node_instance_type" {
  description = "EC2 instance type for the agent node group"
  type        = string
  default     = "t3.large"
}

variable "agent_node_desired" {
  description = "Desired number of agent nodes"
  type        = number
  default     = 2
}

variable "agent_node_min" {
  description = "Minimum number of agent nodes"
  type        = number
  default     = 1
}

variable "agent_node_max" {
  description = "Maximum number of agent nodes"
  type        = number
  default     = 6
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
