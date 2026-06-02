# HECATE — Security Module
# Creates IAM roles, KMS CMKs, and HashiCorp Vault on EKS.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

# ─────────────────────────────────────────────
# KMS Customer Managed Keys
# ─────────────────────────────────────────────

resource "aws_kms_key" "hecate_main" {
  description              = "HECATE main CMK for ${var.environment} — EKS secrets, RDS, S3, MSK"
  deletion_window_in_days  = var.environment == "prod" ? 30 : 7
  enable_key_rotation      = true
  multi_region             = var.environment == "prod"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-main-cmk"
  })
}

resource "aws_kms_alias" "hecate_main" {
  name          = "alias/hecate-${var.environment}-main"
  target_key_id = aws_kms_key.hecate_main.key_id
}

resource "aws_kms_key" "hecate_secrets" {
  description             = "HECATE secrets CMK for ${var.environment} — Secrets Manager"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-secrets-cmk"
  })
}

resource "aws_kms_alias" "hecate_secrets" {
  name          = "alias/hecate-${var.environment}-secrets"
  target_key_id = aws_kms_key.hecate_secrets.key_id
}

# ─────────────────────────────────────────────
# IRSA Helper — IAM role for a K8s service account
# ─────────────────────────────────────────────

locals {
  oidc_provider_url = replace(var.oidc_provider_arn, "/^.*provider\//", "")

  # Agent-to-IAM-policy mappings
  agent_roles = {
    "monitoring-agent" = {
      namespace       = "hecate-agents"
      policy_document = data.aws_iam_policy_document.monitoring_agent.json
    }
    "detection-agent" = {
      namespace       = "hecate-agents"
      policy_document = data.aws_iam_policy_document.detection_agent.json
    }
    "rca-agent" = {
      namespace       = "hecate-agents"
      policy_document = data.aws_iam_policy_document.rca_agent.json
    }
    "decision-agent" = {
      namespace       = "hecate-agents"
      policy_document = data.aws_iam_policy_document.decision_agent.json
    }
    "remediation-agent" = {
      namespace       = "hecate-agents"
      policy_document = data.aws_iam_policy_document.remediation_agent.json
    }
    "reporting-agent" = {
      namespace       = "hecate-agents"
      policy_document = data.aws_iam_policy_document.reporting_agent.json
    }
    "dashboard-service" = {
      namespace       = "hecate-dashboard"
      policy_document = data.aws_iam_policy_document.dashboard_service.json
    }
  }
}

resource "aws_iam_role" "agent" {
  for_each = local.agent_roles

  name = "${var.environment}-hecate-${each.key}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_provider_url}:sub" = "system:serviceaccount:${each.value.namespace}:${each.key}"
          "${local.oidc_provider_url}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-${each.key}-irsa"
  })
}

resource "aws_iam_policy" "agent" {
  for_each = local.agent_roles

  name        = "${var.environment}-hecate-${each.key}-policy"
  description = "IAM policy for HECATE ${each.key} in ${var.environment}"
  policy      = each.value.policy_document

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "agent" {
  for_each = local.agent_roles

  role       = aws_iam_role.agent[each.key].name
  policy_arn = aws_iam_policy.agent[each.key].arn
}

# ─────────────────────────────────────────────
# IAM Policy Documents — Per Agent
# ─────────────────────────────────────────────

data "aws_iam_policy_document" "monitoring_agent" {
  statement {
    sid    = "MSKConnect"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:DescribeCluster",
      "kafka-cluster:WriteData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "CloudWatchMetrics"
    effect = "Allow"
    actions = [
      "cloudwatch:GetMetricData",
      "cloudwatch:ListMetrics",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "SecretsRead"
    effect = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:*:*:secret:${var.environment}/hecate/monitoring-agent/*"]
  }
}

data "aws_iam_policy_document" "detection_agent" {
  statement {
    sid    = "MSKReadWrite"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:ReadData",
      "kafka-cluster:WriteData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "SecretsRead"
    effect = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:*:*:secret:${var.environment}/hecate/detection-agent/*"]
  }
}

data "aws_iam_policy_document" "rca_agent" {
  statement {
    sid    = "MSKReadWrite"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:ReadData",
      "kafka-cluster:WriteData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "EKSDescribe"
    effect = "Allow"
    actions = [
      "eks:DescribeCluster",
      "eks:ListClusters",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "decision_agent" {
  statement {
    sid    = "MSKReadWrite"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:ReadData",
      "kafka-cluster:WriteData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "SSMParameterRead"
    effect = "Allow"
    actions = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = ["arn:aws:ssm:*:*:parameter/hecate/${var.environment}/policies/*"]
  }
}

data "aws_iam_policy_document" "remediation_agent" {
  statement {
    sid    = "MSKReadWrite"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:ReadData",
      "kafka-cluster:WriteData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "EKSRemediations"
    effect = "Allow"
    actions = [
      "eks:DescribeCluster",
      "ec2:DescribeInstances",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "TerraformStateRead"
    effect = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      "arn:aws:s3:::hecate-terraform-state-${var.environment}",
      "arn:aws:s3:::hecate-terraform-state-${var.environment}/*",
    ]
  }
}

data "aws_iam_policy_document" "reporting_agent" {
  statement {
    sid    = "MSKRead"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:ReadData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "SESEmailSend"
    effect = "Allow"
    actions = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "dashboard_service" {
  statement {
    sid    = "MSKRead"
    effect = "Allow"
    actions = [
      "kafka-cluster:Connect",
      "kafka-cluster:ReadData",
      "kafka-cluster:DescribeTopic",
    ]
    resources = ["arn:aws:kafka:*:*:cluster/${var.environment}-hecate-kafka/*"]
  }

  statement {
    sid    = "RDSConnect"
    effect = "Allow"
    actions = ["rds-db:connect"]
    resources = ["arn:aws:rds-db:*:*:dbuser:*/${var.environment}_hecate_dashboard"]
  }
}

# ─────────────────────────────────────────────
# HashiCorp Vault on EKS (via Helm)
# ─────────────────────────────────────────────

resource "helm_release" "vault" {
  name       = "vault"
  repository = "https://helm.releases.hashicorp.com"
  chart      = "vault"
  version    = "0.27.0"
  namespace  = "hecate-system"

  values = [
    yamlencode({
      server = {
        ha = {
          enabled  = var.environment == "prod"
          replicas = var.environment == "prod" ? 3 : 1
        }
        dataStorage = {
          enabled          = true
          storageClass     = "gp3"
          size             = var.environment == "prod" ? "20Gi" : "5Gi"
        }
        affinity = ""
      }
      injector = {
        enabled = true
      }
      ui = {
        enabled         = true
        serviceType     = "ClusterIP"
      }
    })
  ]
}
