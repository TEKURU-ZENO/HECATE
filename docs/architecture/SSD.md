# HECATE v2.0 Software System Design Document (SSD)

## 1. System Topology & Port Assignments

HECATE is partitioned into the following FastAPI Microservices and background Agents:

| Component | Type | Target Port | Primary Tech | Description |
| :--- | :---: | :---: | :---: | :--- |
| **dashboard-api** | Service | `8000` | FastAPI | BFF gateway providing REST & live WebSockets for the UI |
| **anomaly-service** | Service | `8001` | FastAPI | deduplicates anomalies, logs incidents and publishes to `incident-topic` |
| **policy-service** | Service | `8002` | FastAPI | Parses declarative YAML and evaluates OPA-like policy rules |
| **forecasting-service**| Service | `8003` | FastAPI | LSTM time-series forecast engine mapping predicted telemetry spikes |
| **copilot-service** | Service | `8004` | FastAPI | RAG Reasoning Copilot chat backend with RAG/Graph reasoning and Planning Engine |
| **graph-service** | Service | `8005` | FastAPI | Dependency dependency graph service (Neo4j client / NetworkX mock fallback) |
| **digital-twin-service**| Service| `8006` | FastAPI | Models virtual clusters, calculates TwinScore, and processes calibration |

### Background Operational Agents (Event Consumers)
1. **monitoring-agent**: Scrapes CPU/Memory/Restart metric observations.
2. **detection-agent**: Evaluates metric anomalies using Isolation Forest.
3. **prediction-agent**: Listens to forecasts and triggers predictive incidents.
4. **rca-agent**: Performs graph dependency searches.
5. **recommendation-agent**: Recommends playbooks, updating TD Q-values.
6. **simulation-agent**: Simulates playbooks via Twin Service.
7. **decision-agent**: Evaluates risk score and policies.
8. **remediation-agent**: Triggers Kubernetes execution chains.
9. **learning-agent**: Evaluates recovery time and logs effectiveness.

---

## 2. Ingestion Contracts & Message Topics

Communication happens over **10 Kafka topics** (synced to sqlite `hecate_events.db` in mock dev environments):

1. `metrics-topic`: Real-time scrape observations.
2. `anomaly-topic`: Detected threshold and model anomalies.
3. `incident-topic`: Unique incident tickets opened.
4. `rca-topic`: Diagnosed root-cause services.
5. `recommendation-topic`: Playbooks recommended by similarity search.
6. `simulation-topic`: Multi-action simulated playbook sequences.
7. `approval-topic`: Multi-agent human-in-the-loop approval triggers.
8. `decision-topic`: Approved decisions passed for execution.
9. `remediation-topic`: Active playbook execution steps and outcomes.
10. `learning-topic`: Feedback logs consumed for Temporal Difference training.

---

## 3. Database Schema Definitions (HECATE v2.0 Updates)

### 3.1 `twin_memory` Table
Used by `digital-twin-service` to persist simulation predictions and calculate drift against actual telemetry outcomes:
```sql
CREATE TABLE IF NOT EXISTS twin_memory (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    service_name TEXT NOT NULL,
    playbook_sequence TEXT NOT NULL,
    predicted_mttr REAL,
    actual_mttr REAL,
    predicted_cost REAL,
    actual_cost REAL,
    predicted_blast_radius REAL,
    actual_blast_radius REAL,
    prediction_error REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 `playbook_q_values` Table
Maintains adaptive state-action values updated via Temporal Difference reinforcement learning feedback:
```sql
CREATE TABLE IF NOT EXISTS playbook_q_values (
    state_key TEXT NOT NULL,
    action_name TEXT NOT NULL,
    q_value REAL NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (state_key, action_name)
);
```

---

## 4. Design-by-Contract Validation
- **Event Validator Gate**: The Decision Agent cross-references current cluster twin topology on `http://localhost:8006/api/v1/twin/data` to ensure target service existence and topology freshness $\ge 0.7$ before approving executions.
- **Transactional Approval Lock**: Human-in-the-loop decisions acquire serializable DB locks on the `approvals` table to prevent double-execution concurrency race conditions.