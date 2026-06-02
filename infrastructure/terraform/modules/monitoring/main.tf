# HECATE — Monitoring Module
# Deploys Prometheus, Grafana, AlertManager, and Loki on EKS via Helm.

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
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
  }
}

# ─────────────────────────────────────────────
# Namespace
# ─────────────────────────────────────────────

resource "kubernetes_namespace" "observability" {
  metadata {
    name = "hecate-observability"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "app.kubernetes.io/part-of"    = "hecate-platform"
    }
  }
}

# ─────────────────────────────────────────────
# Prometheus + Alertmanager + Grafana
# (kube-prometheus-stack Helm chart)
# ─────────────────────────────────────────────

resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "55.5.0"
  namespace  = kubernetes_namespace.observability.metadata[0].name

  timeout = 600

  values = [
    yamlencode({
      prometheus = {
        prometheusSpec = {
          retention           = var.environment == "prod" ? "30d" : "7d"
          retentionSize       = var.environment == "prod" ? "50GB" : "10GB"
          replicas            = var.environment == "prod" ? 2 : 1
          storageSpec = {
            volumeClaimTemplate = {
              spec = {
                storageClassName = "gp3"
                resources = {
                  requests = { storage = var.environment == "prod" ? "100Gi" : "20Gi" }
                }
              }
            }
          }
          serviceMonitorSelectorNilUsesHelmValues = false
          podMonitorSelectorNilUsesHelmValues     = false
          additionalScrapeConfigs = [
            {
              job_name = "hecate-agents"
              kubernetes_sd_configs = [{ role = "pod" }]
              relabel_configs = [
                {
                  source_labels = ["__meta_kubernetes_pod_annotation_prometheus_io_scrape"]
                  action        = "keep"
                  regex         = "true"
                }
              ]
            }
          ]
        }
      }
      alertmanager = {
        alertmanagerSpec = {
          replicas = var.environment == "prod" ? 2 : 1
        }
        config = {
          global = {
            slack_api_url = var.slack_webhook_url
          }
          route = {
            group_by    = ["alertname", "cluster", "service"]
            receiver    = "hecate-slack"
            group_wait  = "30s"
            group_interval = "5m"
            repeat_interval = "4h"
          }
          receivers = [
            {
              name = "hecate-slack"
              slack_configs = [
                {
                  channel    = "#hecate-alerts"
                  title      = "[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}"
                  text       = "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
                  send_resolved = true
                }
              ]
            }
          ]
        }
      }
      grafana = {
        enabled          = true
        adminPassword    = var.grafana_admin_password
        persistence = {
          enabled          = true
          storageClassName = "gp3"
          size             = "10Gi"
        }
        dashboardProviders = {
          "dashboardproviders.yaml" = {
            apiVersion = 1
            providers = [
              {
                name            = "hecate"
                orgId           = 1
                folder          = "HECATE"
                type            = "file"
                disableDeletion = false
                options = { path = "/var/lib/grafana/dashboards/hecate" }
              }
            ]
          }
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace.observability]
}

# ─────────────────────────────────────────────
# Loki (log aggregation)
# ─────────────────────────────────────────────

resource "helm_release" "loki" {
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki-stack"
  version    = "2.10.2"
  namespace  = kubernetes_namespace.observability.metadata[0].name

  values = [
    yamlencode({
      loki = {
        persistence = {
          enabled          = true
          storageClassName = "gp3"
          size             = var.environment == "prod" ? "50Gi" : "10Gi"
        }
        config = {
          chunk_store_config = {
            max_look_back_period = var.environment == "prod" ? "2160h" : "168h" # 90d vs 7d
          }
        }
      }
      promtail = {
        enabled = true
      }
    })
  ]

  depends_on = [helm_release.kube_prometheus_stack]
}

# ─────────────────────────────────────────────
# S3 bucket for long-term metrics archive
# ─────────────────────────────────────────────

resource "aws_s3_bucket" "metrics_archive" {
  bucket = "${var.environment}-hecate-metrics-archive"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-metrics-archive"
  })
}

resource "aws_s3_bucket_versioning" "metrics_archive" {
  bucket = aws_s3_bucket.metrics_archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "metrics_archive" {
  bucket = aws_s3_bucket.metrics_archive.id

  rule {
    id     = "archive-old-metrics"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}
