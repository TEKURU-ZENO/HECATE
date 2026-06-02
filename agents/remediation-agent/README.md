# remediation-agent
HECATE Remediation Agent — Integrates with Kubernetes to execute mitigation actions

## Responsibilities
* Connect to Kafka bootstrap servers.
* Manage Kafka topics consumer/producer logic.
* Process operational loops.

## Kafka Topics
* Consumed/Produced: See root README.

## Config
* `KAFKA_BOOTSTRAP_SERVERS` (default: localhost:9092)
* `LOG_LEVEL` (default: INFO)