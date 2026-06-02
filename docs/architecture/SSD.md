# Software System Design Document (SSD)

## 1. Core Component Layout
* `telemetry-service`: Receives HTTP metrics/logs.
* `monitoring-agent`: Pulls metrics from Prometheus.
* `detection-agent`: Evaluates telemetry against ML/static rules.
* `rca-agent`: Determines root cause of alerts.
* `decision-agent`: Maps root cause to remediation policy.
* `remediation-agent`: Deploys fix (restart, scale, rollback).
* `learning-agent`: Updates action weights.
* `reporting-agent`: Summarizes incident details.

## 2. Ingestion contracts
Defined in Kafka JSON contracts directory.

## 3. DB schemas
* PostgreSQL holds policy configurations, user credentials, incident history, audit logs.
* TimescaleDB stores telemetry metrics for historical baseline evaluations.