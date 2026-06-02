# High-Level Design (HLD)

## 1. System Overview
HECATE consists of a multi-agent intelligence layer, a telemetry ingestion layer, a persistence layer, and a dashboard presentation layer.

## 2. Data Flow
Telemetry Ingestion -> Kafka raw metrics -> Detection -> Kafka Anomalies -> RCA -> Kafka RCA -> Decision -> Kafka Decisions -> Remediation -> Kafka Remediation -> Learning & Reporting.