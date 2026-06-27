variable "aws_region" {
  type        = string
  description = "Target AWS Region"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  default     = "prod"
}

variable "db_instance_class" {
  type        = string
  description = "RDS DB instance size"
  default     = "db.t3.micro"
}

variable "db_password" {
  type        = string
  description = "Relational database root user password"
  sensitive   = true
  default     = "HECATE_Secure_DB_Pass_2026!"
}
