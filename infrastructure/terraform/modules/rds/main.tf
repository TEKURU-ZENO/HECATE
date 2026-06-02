# HECATE — RDS Module
# Creates a PostgreSQL RDS instance for incident and audit log storage.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# ─────────────────────────────────────────────
# Random password for RDS master user
# ─────────────────────────────────────────────

resource "random_password" "rds_master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"
}

# ─────────────────────────────────────────────
# Store password in AWS Secrets Manager
# ─────────────────────────────────────────────

resource "aws_secretsmanager_secret" "rds_master" {
  name                    = "${var.environment}/hecate/rds/master-credentials"
  description             = "HECATE RDS master credentials for ${var.environment}"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
  kms_key_id              = var.kms_key_arn

  tags = var.common_tags
}

resource "aws_secretsmanager_secret_version" "rds_master" {
  secret_id = aws_secretsmanager_secret.rds_master.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.rds_master.result
    host     = aws_db_instance.hecate.address
    port     = aws_db_instance.hecate.port
    dbname   = var.db_name
  })
}

# ─────────────────────────────────────────────
# DB Subnet Group
# ─────────────────────────────────────────────

resource "aws_db_subnet_group" "hecate" {
  name        = "${var.environment}-hecate-rds-subnet-group"
  subnet_ids  = var.private_subnet_ids
  description = "Subnet group for HECATE RDS in ${var.environment}"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-rds-subnet-group"
  })
}

# ─────────────────────────────────────────────
# DB Parameter Group
# ─────────────────────────────────────────────

resource "aws_db_parameter_group" "hecate" {
  name        = "${var.environment}-hecate-postgres15"
  family      = "postgres15"
  description = "Custom parameter group for HECATE PostgreSQL 15"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log queries taking > 1s
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# RDS Instance
# ─────────────────────────────────────────────

resource "aws_db_instance" "hecate" {
  identifier = "${var.environment}-hecate-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = var.db_instance_class
  parameter_group_name = aws_db_parameter_group.hecate.name

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = var.kms_key_arn

  # Credentials
  db_name  = var.db_name
  username = var.db_username
  password = random_password.rds_master.result

  # Network
  db_subnet_group_name   = aws_db_subnet_group.hecate.name
  vpc_security_group_ids = [var.rds_sg_id]
  publicly_accessible    = false
  port                   = 5432

  # Backup & Maintenance
  backup_retention_period = var.environment == "prod" ? 30 : 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"
  copy_tags_to_snapshot   = true
  skip_final_snapshot     = var.environment == "prod" ? false : true
  final_snapshot_identifier = var.environment == "prod" ? "${var.environment}-hecate-final-snapshot" : null

  # High Availability
  multi_az = var.multi_az

  # Deletion protection
  deletion_protection = var.environment == "prod" ? true : false

  # Monitoring
  performance_insights_enabled          = true
  performance_insights_retention_period = var.environment == "prod" ? 731 : 7
  performance_insights_kms_key_id       = var.kms_key_arn
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]

  # Auto minor version upgrades
  auto_minor_version_upgrade = var.environment != "prod"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-postgres"
  })
}

# ─────────────────────────────────────────────
# Enhanced Monitoring IAM Role
# ─────────────────────────────────────────────

resource "aws_iam_role" "rds_monitoring" {
  name = "${var.environment}-hecate-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ─────────────────────────────────────────────
# Read Replica (prod only)
# ─────────────────────────────────────────────

resource "aws_db_instance" "hecate_replica" {
  count = var.environment == "prod" ? 1 : 0

  identifier             = "${var.environment}-hecate-postgres-replica"
  replicate_source_db    = aws_db_instance.hecate.identifier
  instance_class         = var.db_instance_class
  storage_encrypted      = true
  kms_key_id             = var.kms_key_arn
  publicly_accessible    = false
  vpc_security_group_ids = [var.rds_sg_id]

  performance_insights_enabled = true
  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_monitoring.arn

  auto_minor_version_upgrade = false
  skip_final_snapshot        = true

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-postgres-replica"
  })
}
