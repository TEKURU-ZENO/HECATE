# HECATE — Kafka Topic Contracts

This directory contains the **contract-first** schemas for every Kafka topic used by the HECATE platform. Each JSON file is a valid [JSON Schema draft-07](https://json-schema.org/draft-07/json-schema-validation.html) document that defines the canonical shape of events flowing through the system.

---

## Contract-First Philosophy

HECATE follows a **contract-first** approach to event-driven communication:

1. **Schema is the source of truth.** Before any agent produces or consumes a topic, its event schema must be defined and reviewed here.
2. **Backward compatibility is enforced.** Breaking schema changes require a major version bump and a migration path.
3. **Consumers validate at runtime.** Every agent uses [jsonschema](https://python-jsonschema.readthedocs.io/) to validate incoming events against the corresponding contract before processing.
4. **Producers validate before publishing.** Events that fail schema validation are routed to a dead-letter topic (`<topic>.dlq`) and an alert is raised.

---

## Topic Registry

| JSON File | Kafka Topic | Producer | Consumer(s) |
|---|---|---|---|
| `metrics-topic.json` | `hecate.metrics` | Monitoring Agent | Detection Agent, Reporting Agent |
| `anomaly-topic.json` | `hecate.anomalies` | Detection Agent | RCA Agent, Reporting Agent |
| `rca-topic.json` | `hecate.rca` | RCA Agent | Decision Agent, Reporting Agent |
| `decision-topic.json` | `hecate.decisions` | Decision Agent | Remediation Agent, Reporting Agent |
| `remediation-topic.json` | `hecate.remediation` | Remediation Agent | Reporting Agent |
| `reporting-topic.json` | `hecate.reports` | Reporting Agent | Dashboard Service |

---

## Schema Version Policy

Each schema file contains a `schema_version` field that follows [Semantic Versioning](https://semver.org/):

- **PATCH** (`1.0.x`): Documentation or description changes only.
- **MINOR** (`1.x.0`): Backward-compatible additions (new optional fields).
- **MAJOR** (`x.0.0`): Breaking changes — new required fields, renamed fields, type changes.

All major version bumps must be coordinated across producer and consumer services simultaneously. A migration window of **2 sprint cycles** is the minimum allowed before deprecating an old schema version.

---

## Validation Utilities

Shared validation code lives in `shared/kafka/` and is published as an internal Python package (`hecate-contracts`). Each agent imports it as:

```python
from hecate.contracts import validate_event, METRICS_SCHEMA, ANOMALY_SCHEMA
```

---

## Adding a New Contract

1. Create a new `<topic-name>-topic.json` file following the patterns in this directory.
2. Register the topic in the table above.
3. Update `shared/kafka/schemas.py` to import the new schema.
4. Open a PR and tag both the producing and consuming agent owners for review.
5. Deploy the schema change to MSK Schema Registry before deploying any agent code.

---

## Dead-Letter Queue (DLQ) Convention

Every topic has a corresponding DLQ named `<topic>.dlq`. Events are routed there with the following envelope:

```json
{
  "original_event": { "...": "original payload" },
  "validation_errors": ["field 'event_id' is required"],
  "received_at": "2025-01-15T10:30:00Z",
  "source_topic": "hecate.metrics"
}
```
