# HECATE Observability Stack

> **Full-stack observability for the HECATE autonomous reliability platform** — metrics, traces, logs, and alerts in a unified pipeline.

---

## Overview

The HECATE observability stack is built on four battle-tested open-source pillars:

| Pillar | Tool | Port | Purpose |
|--------|------|------|---------|
| **Metrics** | Prometheus | 9090 | Time-series scraping & alerting |
| **Visualization** | Grafana | 3000 | Dashboards & alert routing |
| **Distributed Tracing** | Jaeger | 16686 | End-to-end request tracing |
| **Log Aggregation** | Elasticsearch + Kibana | 9200 / 5601 | Structured log search & analysis |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      HECATE Agents & Services                   │
│  monitoring-agent │ detection-agent │ rca-agent │ remediation   │
└────────┬──────────────────┬────────────────┬────────────────────┘
         │ /metrics         │ OTLP traces    │ Structured logs
         ▼                  ▼                ▼
  ┌────────────┐    ┌──────────────┐  ┌──────────────────┐
  │ Prometheus │    │    Jaeger    │  │  Elasticsearch   │
  │  :9090     │    │   :16686     │  │     :9200        │
  └──────┬─────┘    └──────────────┘  └────────┬─────────┘
         │                                      │
         ▼                                      ▼
  ┌────────────┐                        ┌──────────────┐
  │  Grafana   │◄───────────────────────│    Kibana    │
  │  :3000     │    (datasource)        │   :5601      │
  └──────┬─────┘                        └──────────────┘
         │
         ▼
  ┌──────────────┐
  │ AlertManager │
  │   :9093      │
  └──────────────┘
```

---

## Components

### Prometheus
Located in `prometheus/`. Handles:
- **Scrape configs** for all HECATE agents and Kubernetes nodes
- **Alert rules** (`alert_rules.yml`) — infrastructure and agent health alerts
- **Recording rules** (`recording_rules.yml`) — pre-aggregated metrics for dashboard performance

Key alert groups:
- `hecate.infrastructure` — CPU, memory, pod crash looping, error rates
- `hecate.agents` — individual agent health and Kafka consumer lag

### Grafana
Located in `grafana/`. Pre-configured with:
- **Datasources** — Prometheus and Elasticsearch (auto-provisioned)
- **Dashboards** — Service Health and Incident Overview (auto-provisioned)
- **Provisioning** — zero-click setup via `provisioning/`

Dashboard inventory:

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| Service Health | `hecate-service-health` | CPU, memory, error rate, latency |
| Incident Overview | `hecate-incident-overview` | Incident count, MTTR, severity distribution |

### Jaeger
Located in `jaeger/`. Provides distributed tracing for:
- Kafka message processing chains
- Agent-to-agent decision flows
- Service RPC calls

### Elasticsearch
Located in `elasticsearch/`. Manages:
- **Index templates** — structured log schemas with proper mappings
- **ILM policies** — hot → warm → delete lifecycle (30-day total retention)

---

## Quick Start

```bash
# Start the full observability stack
docker compose -f docker-compose.yml up -d prometheus grafana jaeger elasticsearch kibana alertmanager

# Verify all services are healthy
./scripts/health-check.sh

# Access dashboards
open http://localhost:3000   # Grafana (admin/admin)
open http://localhost:9090   # Prometheus
open http://localhost:16686  # Jaeger
open http://localhost:5601   # Kibana
```

---

## Alerting

Alerts are routed through AlertManager (`alertmanager:9093`) and can be forwarded to:
- **Slack** — `#hecate-alerts` channel
- **PagerDuty** — for critical severity
- **Email** — for weekly summaries

To add a new alert, edit `prometheus/alert_rules.yml` and reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

---

## Adding New Dashboards

1. Create or export the dashboard JSON from Grafana UI
2. Save it to `grafana/dashboards/<name>.json`
3. Grafana auto-reloads dashboards every 10 seconds (see `provisioning/dashboards.yml`)

---

## Runbooks

| Alert | Runbook |
|-------|---------|
| `HighCPUUsage` | Check pod resource limits; scale horizontally if needed |
| `PodCrashLooping` | `kubectl logs <pod> --previous` to inspect crash reason |
| `ServiceHighErrorRate` | Check Jaeger traces for the failing service |
| `HecateAgentDown` | Restart agent pod; check Kafka connectivity |
