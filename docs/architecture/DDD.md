# Database Design Document (DDD)

## 1. Schema Specifications
### PostgreSQL Schema:
* `users`: User authentication, roles (RBAC).
* `incidents`: ID, title, status, severity, root_cause, confidence, detected_at, resolved_at.
* `remediations`: ID, incident_id, action_type, status, success, duration_ms, executed_at.
* `policies`: ID, policy_name, condition, action, risk_level, enabled.

### TimescaleDB:
* `metrics_cpu`, `metrics_memory`, `metrics_network` hyper-tables for fast time-series queries.