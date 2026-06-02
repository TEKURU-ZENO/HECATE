# HECATE — Redis (ElastiCache) Module
# Creates a Redis replication group for caching, session state, and pub/sub.

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
# ElastiCache Subnet Group
# ─────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "hecate" {
  name        = "${var.environment}-hecate-redis-subnet-group"
  subnet_ids  = var.private_subnet_ids
  description = "Subnet group for HECATE Redis in ${var.environment}"

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# ElastiCache Parameter Group
# ─────────────────────────────────────────────

resource "aws_elasticache_parameter_group" "hecate" {
  name        = "${var.environment}-hecate-redis7"
  family      = "redis7"
  description = "Custom parameter group for HECATE Redis 7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "Ex" # Expired key events for cache invalidation
  }

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# Redis Security Group
# ─────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name        = "${var.environment}-hecate-redis-sg"
  description = "Security group for HECATE ElastiCache Redis"
  vpc_id      = var.vpc_id

  ingress {
    description = "Redis from private subnets"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-redis-sg"
  })
}

# ─────────────────────────────────────────────
# Redis Replication Group
# ─────────────────────────────────────────────

resource "aws_elasticache_replication_group" "hecate" {
  replication_group_id = "${var.environment}-hecate-redis"
  description          = "HECATE Redis cluster for ${var.environment}"

  # Engine
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.node_type
  parameter_group_name = aws_elasticache_parameter_group.hecate.name
  port                 = 6379

  # Cluster mode
  num_cache_clusters = var.environment == "prod" ? 3 : 1

  # Network
  subnet_group_name  = aws_elasticache_subnet_group.hecate.name
  security_group_ids = [aws_security_group.redis.id]

  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = var.kms_key_arn

  # Availability
  automatic_failover_enabled = var.environment == "prod" ? true : false
  multi_az_enabled           = var.environment == "prod" ? true : false

  # Maintenance
  maintenance_window       = "Mon:05:00-Mon:06:00"
  snapshot_retention_limit = var.environment == "prod" ? 7 : 1
  snapshot_window          = "04:00-05:00"

  # Notifications
  notification_topic_arn = var.sns_topic_arn

  apply_immediately = var.environment != "prod"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-redis"
  })
}
