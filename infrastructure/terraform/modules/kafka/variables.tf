variable "environment" {
  type        = string
  description = "Target deployment environment"
}
variable "broker_node_type" {
  type        = string
  default     = "kafka.m5.large"
}