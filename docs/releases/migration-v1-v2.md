# HECATE v1.0 to v2.0 Migration Guide

This guide details the steps to migrate HECATE deployments from version 1.0 to 2.0 Production Edition.

## Database Migrations
Version 2.0 introduces multi-tenancy and simulation memory tables. Run the CLI doctor command or execute these migrations:

```sql
-- Add tenant_id columns for isolation
ALTER TABLE incidents ADD COLUMN tenant_id TEXT DEFAULT 'default';
ALTER TABLE policies ADD COLUMN tenant_id TEXT DEFAULT 'default';
ALTER TABLE operational_memory ADD COLUMN tenant_id TEXT DEFAULT 'default';
ALTER TABLE approvals ADD COLUMN tenant_id TEXT DEFAULT 'default';
ALTER TABLE users ADD COLUMN tenant_id TEXT DEFAULT 'default';

-- Create twin memory and SRE KPI tables
CREATE TABLE IF NOT EXISTS twin_memory (
    id TEXT PRIMARY KEY,
    incident_id TEXT,
    service_name TEXT,
    playbook_sequence TEXT,
    predicted_mttr REAL,
    actual_mttr REAL,
    predicted_cost REAL,
    actual_cost REAL,
    predicted_blast_radius REAL,
    actual_blast_radius REAL,
    prediction_error REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sre_metrics (
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mttr_seconds REAL,
    mtbf_hours REAL,
    availability_pct REAL,
    error_budget_remaining_pct REAL,
    slo_compliance_pct REAL,
    sla_compliance_pct REAL,
    incident_frequency INTEGER,
    recovery_success_rate REAL,
    prediction_accuracy REAL,
    false_positive_rate REAL,
    simulation_accuracy REAL,
    recommendation_accuracy REAL
);
```

## Environment Configuration
You must configure the following new environment variables:
- `HECATE_ENV`: Set to `dev`, `staging`, `prod`, or `testing` (replaces old static `config.py`).
- `DECISION_SIGNING_KEY`: SHA256 HMAC secret key shared between the Decision Agent and the Remediation Agent.
