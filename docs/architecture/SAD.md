# Software Architecture Document (SAD)

## 1. Architectural Vision
HECATE is built as an event-driven, microservices-based monorepo, where specialized autonomous agents communicate asynchronously via Apache Kafka.

## 2. Architectural Principles
* **AP-01**: Event-driven loose coupling.
* **AP-02**: Agent isolation (each agent does one job).
* **AP-03**: Self-healing runtime (HECATE runs on Kubernetes, self-monitoring).
* **AP-04**: Design by contract (defined Kafka schemas).

## 3. Core Layers
1. **Telemetry Layer**: Prometheus scrapes and Ingestion APIs.
2. **Streaming & Event Backbone**: Apache Kafka.
3. **Detection Layer**: Rule evaluators and ML inference.
4. **Diagnosis Layer (RCA)**: Graph-based dependency analysis.
5. **Mitigation Layer**: Decision engine and Kubernetes executers.
6. **Persistence Layer**: Postgres, TimescaleDB, Redis, Elasticsearch.
7. **Presentation Layer**: React dashboard and FastAPI APIs.