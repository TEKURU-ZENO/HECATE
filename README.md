# HECATE — Heuristic Engine for Cloud Automation, Telemetry & Execution
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Kubernetes-blue)
![Status](https://img.shields.io/badge/Status-Active_Development-green)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)
![Kafka](https://img.shields.io/badge/Apache_Kafka-3.6-231F20?logo=apachekafka)
> **An Autonomous AI-Native Cloud Reliability Platform for Self-Healing Infrastructure**
HECATE continuously monitors Kubernetes-based cloud infrastructure, detects anomalies in real time, performs root cause analysis, and autonomously remediates incidents — reducing MTTR from hours to seconds.
---
## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [Components](#components)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Author](#author)
---
## Overview
Modern cloud-native applications running on Kubernetes are complex, dynamic, and failure-prone. Site reliability engineers (SREs) spend significant portions of their time triaging incidents, correlating metrics, and executing the same remediation playbooks repeatedly. This reactive posture creates alert fatigue, slows down MTTR, and introduces human error.
**HECATE** solves this problem by bringing autonomous intelligence to cloud reliability engineering. It is a multi-agent AI system that:
1. **Observes** — Continuously ingests telemetry (metrics, logs, traces, events) from your Kubernetes clusters via Prometheus, Loki, and the Kubernetes API server.
2. **Detects** — Applies rule-based and ML-driven (Isolation Forest, LSTM autoencoders) anomaly detection to identify deviations from baseline behavior before they become incidents.
3. **Diagnoses** — Uses a graph-based root cause analysis (RCA) engine that traverses the service dependency graph to pinpoint the origin of failures with high confidence.
4. **Decides** — A policy-governed decision engine evaluates the risk level and urgency of each incident, selecting from a library of remediation actions ranked by predicted effectiveness.
5. **Remediates** — Autonomously executes safe, audited remediation actions against the Kubernetes API (pod restarts, scaling, rollbacks, resource adjustments) or escalates to the on-call engineer.
6. **Learns** — Closes the feedback loop by recording remediation outcomes, updating the confidence model, and continuously improving detection and decision quality.
7. **Reports** — Generates structured incident reports with full audit trails, RCA summaries, and MTTR metrics for compliance and continuous improvement.
HECATE is designed from the ground up to be cloud-native, event-driven, observable, and extensible.
---
## Architecture
HECATE is organized into **7 functional layers**, each implemented as one or more independent microservices communicating over Apache Kafka:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HECATE PLATFORM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 7 — PRESENTATION                                              │   │
│  │  React 18 Dashboard  │  FastAPI REST  │  Grafana Dashboards          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 6 — REPORTING & AUDIT                                         │   │
│  │  Reporting Agent  │  Incident Store (PG)  │  Audit Log (ES)          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5 — LEARNING & ADAPTATION                                     │   │
│  │  Learning Agent  │  MLflow  │  Feature Store  │  Model Registry      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4 — REMEDIATION EXECUTION                                     │   │
│  │  Remediation Agent  │  Kubernetes API Client  │  GitOps (ArgoCD)     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3 — DECISION & POLICY                                         │   │
│  │  Decision Agent  │  Policy Engine  │  Risk Scorer  │  Redis Cache    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2 — INTELLIGENCE                                              │   │
│  │  Detection Agent  │  RCA Agent  │  Anomaly Engine  │  Graph Engine   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1 — TELEMETRY INGESTION                                       │   │
│  │  Monitoring Agent  │  Prometheus  │  Kafka Streams  │  TimescaleDB   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 0 — INFRASTRUCTURE                                            │   │
│  │  AWS EKS  │  Terraform  │  ArgoCD  │  Kubernetes  │  Helm            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    ←──────── Apache Kafka Event Bus ────────→
                    ←──────── OpenTelemetry (OTEL) ──────────→
```
### Event Flow
```
K8s Cluster ──► Monitoring Agent ──► [metrics-topic] ──► Detection Agent ──► [anomaly-topic] ──► RCA Agent ──► [rca-topic] ──► Recommendation Agent ──► [recommendation-topic] ──► Simulation Agent ──► [simulation-topic] ──► Decision Agent ──► [decision-topic] ──► Remediation Agent ──► K8s API
                                                                                                                                                                                                                                                                          │
                                                                                                                                                                                                                                                                [remediation-topic]
                                                                                                                                                                                                                                                                          │
                                                                                                                                                                                                                                                                Learning Agent ──► [learning-topic] ──► Rec Agent (TD Update)
                                                                                                                                                                                                                                                                Reporting Agent
```
---
## Key Features
### 🤖 Autonomous Remediation
HECATE can execute a library of remediation actions (pod restarts, HPA scaling, rollbacks, resource quota adjustments) entirely without human intervention, governed by configurable risk policies.
### 🔍 Multi-Modal Anomaly Detection
Combines statistical baselines, rule-based thresholds, Isolation Forest (unsupervised), and LSTM autoencoders for time-series anomaly detection across CPU, memory, latency, and error rate signals.
### 🌐 Graph-Based Root Cause Analysis
Builds a real-time service dependency graph from Kubernetes metadata and traces, then traverses it using a correlation-based propagation algorithm to identify the true root cause of failures.
### 🧠 Multi-Agent Architecture
Seven specialized AI agents collaborate over an event-driven Kafka bus, each owning a specific slice of the reliability lifecycle. Agents are independently deployable, scalable, and fault-tolerant.
### 📋 Policy-Governed Decisions
A declarative policy engine governs all automated actions. Policies define conditions, risk thresholds, and allowed actions — ensuring HECATE operates within safe operational boundaries at all times.
### 📊 Full Observability
Every agent action, decision, and remediation is captured in an immutable audit log. OpenTelemetry spans correlate actions across the entire pipeline. Pre-built Grafana dashboards surface MTTR, incident trends, and model accuracy.
### 🔁 Continuous Learning
Post-incident feedback (was the remediation successful? did the anomaly recur?) is fed back into the model training pipeline, continuously improving detection precision and reducing false positives.
### 🔒 Enterprise Security
Mutual TLS between services, RBAC enforced at the API and Kubernetes levels, secret management via HashiCorp Vault, and full audit trails satisfy enterprise compliance requirements.
---
## Technology Stack
| Layer | Technology | Purpose |
|---|---|---|
| **Infrastructure** | AWS EKS, Terraform, Helm, ArgoCD | Kubernetes runtime, IaC, GitOps |
| **Observability** | Prometheus, Grafana, Jaeger, Loki, OpenTelemetry | Metrics, dashboards, tracing, logging |
| **Streaming** | Apache Kafka 3.6 (KRaft), Kafka UI | Event backbone, inter-agent messaging |
| **AI / ML** | Scikit-learn, PyTorch, MLflow, Hugging Face | Anomaly detection, RCA, model lifecycle |
| **Backend** | FastAPI, Python 3.11, Celery, Pydantic v2 | REST API, task queue, schema validation |
| **Databases** | PostgreSQL 16, TimescaleDB, Redis 7, Elasticsearch 8 | Relational, time-series, cache, search |
| **Frontend** | React 18, TypeScript, Vite, Recharts | Dashboard UI, real-time updates |
| **GitOps** | ArgoCD, GitHub Actions | Continuous delivery, CI |
| **Security** | HashiCorp Vault, cert-manager, OPA | Secrets, TLS, policy enforcement |
---
## Repository Structure
```
HECATE/
├── README.md                          # This file
├── LICENSE                            # MIT License
├── CONTRIBUTING.md                    # Contributor guide
├── CHANGELOG.md                       # Version history
├── CODE_OF_CONDUCT.md                 # Community standards
├── SECURITY.md                        # Vulnerability reporting
├── ROADMAP.md                         # Development roadmap
├── .gitignore                         # Git ignore rules
├── .env.example                       # Environment variable template
├── docker-compose.yml                 # Local dev stack
├── Makefile                           # Developer shortcuts
├── pyproject.toml                     # Python tooling config
│
├── agents/                            # All seven autonomous agents
│   ├── monitoring/                    # Layer 1: Telemetry ingestion
│   ├── detection/                     # Layer 2a: Anomaly detection
│   ├── rca/                           # Layer 2b: Root cause analysis
│   ├── decision/                      # Layer 3: Decision & policy
│   ├── remediation/                   # Layer 4: Remediation execution
│   ├── learning/                      # Layer 5: Feedback & retraining
│   └── reporting/                     # Layer 6: Incident reporting
│
├── shared/                            # Shared libraries across agents
│   ├── kafka/                         # Kafka client wrappers
│   ├── models/                        # Pydantic domain models
│   ├── db/                            # Database access layer
│   ├── config/                        # Configuration management
│   └── telemetry/                     # OpenTelemetry setup
│
├── dashboard/                         # HECATE web dashboard
│   ├── frontend/                      # React 18 + TypeScript + Vite
│   └── api/                           # FastAPI backend (BFF)
│
├── infrastructure/                    # Infrastructure as Code
│   ├── terraform/                     # AWS EKS, VPC, RDS, ElastiCache
│   └── kubernetes/                    # Kubernetes manifests (Kustomize)
│       ├── base/                      # Base manifests
│       └── overlays/                  # Environment overlays (dev, prod)
│
├── observability/                     # Observability configuration
│   ├── prometheus/                    # Scrape configs, alert rules
│   ├── grafana/                       # Dashboard JSON provisioning
│   └── otel-collector/                # OpenTelemetry Collector config
│
├── schemas/                           # Kafka event schemas (JSON Schema)
│   ├── metrics.schema.json
│   ├── anomaly.schema.json
│   ├── rca.schema.json
│   ├── decision.schema.json
│   ├── remediation.schema.json
│   └── report.schema.json
│
├── tests/                             # All test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                           # Utility and operational scripts
│
└── docs/                              # Project documentation
    ├── prd/                           # Product Requirements Document
    ├── architecture/                  # SAD, SSD, HLD, DDD, LLD
    ├── adr/                           # Architecture Decision Records
    ├── diagrams/                      # C4 Mermaid diagrams
    ├── governance/                    # RBAC, policy framework
    ├── operations/                    # On-call guides
    ├── runbooks/                      # Incident runbooks
    ├── roadmap/                       # Phase roadmap
    ├── mlops/                         # ML model lifecycle
    └── security/                      # Threat model, security controls
```
---
## Quick Start
### Prerequisites
| Requirement | Version | Installation |
|---|---|---|
| Docker Desktop | 24.x+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | v2.x+ | Bundled with Docker Desktop |
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 20 LTS | [nodejs.org](https://nodejs.org/) |
| kubectl | 1.28+ | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |
| make | Any | Bundled with Linux/macOS, [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm) on Windows |
### 1. Clone the Repository
```bash
git clone https://github.com/devmehta/hecate.git
cd hecate
```
### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration values
# At minimum, set strong passwords for POSTGRES_PASSWORD, REDIS_PASSWORD, JWT_SECRET_KEY
```
### 3. Start the Local Dev Stack
```bash
docker-compose up -d
```
Wait for all services to become healthy (approximately 60–90 seconds):
```bash
docker-compose ps
```
### 4. Start the Agent Pipeline
```bash
make install   # Install Python dependencies
make dev       # Start all HECATE agents (development mode)
```
### 5. Access the Services
| Service | URL | Credentials |
|---|---|---|
| HECATE Dashboard | http://localhost:8000 | See `.env` |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Kafka UI | http://localhost:8080 | — |
| Jaeger UI | http://localhost:16686 | — |
| Kibana | http://localhost:5601 | — |
| Digital Twin Service | http://localhost:8006 | — |
| Elasticsearch | http://localhost:9200 | — |
### 6. Run the Test Suite
```bash
make test
make test-coverage
```
---
## Components
| Component | Layer | Description | Docs |
|---|---|---|---|
| **Monitoring Agent** | Telemetry | Scrapes Prometheus, Kubernetes events; publishes to `metrics-topic` | [agents/monitoring](agents/monitoring/) |
| **Detection Agent** | Intelligence | Consumes metrics; applies rule + ML anomaly detection | [agents/detection](agents/detection/) |
| **RCA Agent** | Intelligence | Graph traversal for root cause identification | [agents/rca](agents/rca/) |
| **Decision Agent** | Decision | Policy evaluation, action selection, risk scoring | [agents/decision](agents/decision/) |
| **Remediation Agent** | Remediation | Kubernetes API execution of approved actions | [agents/remediation](agents/remediation/) |
| **Learning Agent** | Adaptation | Outcome feedback, model retraining orchestration | [agents/learning](agents/learning/) |
| **Reporting Agent** | Reporting | Incident report generation, audit logging | [agents/reporting](agents/reporting/) |
| **Simulation Agent** | Intelligence | Coordinates simulations and scoring between recommendations and twin | [agents/simulation-agent](agents/simulation-agent/) |
| **Digital Twin Service** | Simulation | API service modeling cluster states and evaluating multi-action recovery plans | [services/digital-twin-service](services/digital-twin-service/) |
| **Dashboard API** | Presentation | FastAPI BFF for the frontend | [dashboard/api](dashboard/api/) |
| **Dashboard Frontend** | Presentation | React 18 real-time operations dashboard | [dashboard/frontend](dashboard/frontend/) |
| **Kafka Bus** | Infrastructure | Event backbone (6 topics) | [schemas/](schemas/) |
---
## Roadmap
| Phase | Timeline | Theme | Key Deliverables |
|---|---|---|---|
| **Phase 1** | Q3 2024 | Foundation | Repo scaffold, architecture docs, local dev stack, Kafka topics, schema definitions |
| **Phase 2** | Q4 2024 | Core Pipeline | All 7 agents (skeleton → functional), PostgreSQL schema, TimescaleDB setup, Dashboard v1 |
| **Phase 3** | Q1 2025 | Intelligence | Isolation Forest detection, graph-based RCA, policy engine v1, Kubernetes remediation |
| **Phase 4** | Q2 2025 | Production Hardening | LSTM detection, MLflow integration, full Terraform/EKS deployment, mTLS, Vault |
| **Phase 5** | Q3 2025 | Enterprise | Multi-cluster, fine-tuned LLM for RCA narratives, SLA dashboards, SOC2 readiness |
See [ROADMAP.md](ROADMAP.md) and [docs/roadmap/](docs/roadmap/) for detailed phase breakdowns.
---
## Contributing
We welcome contributions from the community! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.
Key guidelines:
- Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages
- All new code must include unit tests (≥80% coverage on changed files)
- Run `make lint` and `make test` before opening a PR
- Reference the relevant ADR or architecture doc for significant changes
---
## Security
For reporting security vulnerabilities, please see [SECURITY.md](SECURITY.md). Do **not** create public GitHub issues for security vulnerabilities.
---
## License
This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
---
## Author
**Dev Mehta**
- Building HECATE as a flagship autonomous SRE platform
- Focused on AI-native infrastructure reliability at scale
---
*"The goal of HECATE is not to replace SREs, but to give them superpowers."*