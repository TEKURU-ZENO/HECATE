# Grafana for HECATE

This directory contains Grafana configuration for the HECATE observability stack, managed entirely through provisioning (no manual UI configuration required).

---

## Directory Layout

```
grafana/
├── datasources/
│   ├── prometheus.yml       # Prometheus datasource (default)
│   └── elasticsearch.yml    # Elasticsearch datasource for logs
├── dashboards/
│   ├── service-health.json      # CPU, memory, error rate, latency
│   └── incident-overview.json   # Incident count, MTTR, severity
└── provisioning/
    └── dashboards.yml       # Dashboard provider config
```

---

## Provisioned Datasources

| Name | Type | URL | Default |
|------|------|-----|---------|
| Prometheus | prometheus | http://prometheus:9090 | ✅ Yes |
| Elasticsearch | elasticsearch | http://elasticsearch:9200 | ❌ No |

---

## Provisioned Dashboards

| Dashboard | UID | File |
|-----------|-----|------|
| HECATE — Service Health | `hecate-service-health` | `dashboards/service-health.json` |
| HECATE — Incident Overview | `hecate-incident-overview` | `dashboards/incident-overview.json` |

---

## Access

```
URL:      http://localhost:3000
Username: admin
Password: admin  (change on first login)
```

---

## Adding Dashboards

1. Design the dashboard in the Grafana UI
2. Go to **Dashboard → Share → Export → Save to file**
3. Save the JSON to `grafana/dashboards/<name>.json`
4. Grafana reloads dashboards every 10 seconds automatically

---

## Docker Compose Integration

Mount these directories in your `docker-compose.yml`:

```yaml
grafana:
  image: grafana/grafana:10.2.0
  volumes:
    - ./observability/grafana/datasources:/etc/grafana/provisioning/datasources
    - ./observability/grafana/provisioning:/etc/grafana/provisioning/dashboards
    - ./observability/grafana/dashboards:/etc/grafana/dashboards
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_USERS_ALLOW_SIGN_UP=false
```
