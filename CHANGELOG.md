# Changelog

All notable changes to HECATE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [2.0.5] - 2026-06-28

### Added
- **HECATE v2.0.5 — Research Evaluation Harness**
  - Modular evaluation package (`evaluation/`) separating core context, metrics, registry, generators, and reports.
  - Failure scenario registry mapping CPU spikes, memory leaks, DNS failures, packet loss, pod crashes, Kafka outages, and API timeouts.
  - Interactive HTML evaluation dashboard with styled inline SVGs, Markdown executive reports, and vector SVG paper figures.
  - Welch's t-test, Mann-Whitney U, Cohen's d effect size, and bootstrap confidence intervals.
  - Git-style performance delta diff comparison CLI tool.

## [2.0.0] - 2026-06-27

### Added
- **HECATE v2.0 — Autonomous Infrastructure Simulation & Planning** (Major Upgrade)
  - Standalone `digital-twin-service` (port 8006) for multi-cloud, multi-cluster sequence simulations, custom confidence metrics, and post-execution reality calibration loop.
  - New `simulation-agent` that matches playbooks, queries digital twin simulations, and calculates `TwinScore`.
  - Upgraded `policy-service` to parse declarative YAML constraints and evaluate actions (`approve`, `reject`, `escalate`) OPA-style.
  - Upgraded `decision-agent` executing risk calculations post-simulation and enforcing a new **Execution Validator** check (verifying target liveness, topology freshness, and auto-resolution).
  - Upgraded `recommendation-agent` utilizing Adaptive Policy Learning via Temporal Difference (TD) Q-value updates from learning feedback.
  - Upgraded `copilot-service` isolating a `PlanningEngine` to generate markdown comparison tables for recovery strategies.
  - React Vite **Twin Explorer Dashboard UI** page `/twin` displaying multi-cluster mapping, side-by-side states, and calibration control panel.
  - Complete monorepo database schema expansion supporting `twin_memory` and `playbook_q_values` tables.
  - 7 new E2E verification scenarios (Scenarios 19–25) covering twin simulation, policy checks, TD learning, planning engine QA, accuracy calculations, feedback calibration, and plan comparisons.

### In Progress
- Monitoring Agent: Prometheus scrape loop, Kubernetes event watcher
- Detection Agent: Rule-based engine skeleton
- Dashboard API: FastAPI app scaffold, JWT auth middleware
- Dashboard Frontend: React 18 + Vite project scaffold, real-time WebSocket feed

---

## [0.1.0] - 2024-06-01

### Added

#### Repository & Documentation
- Initial repository scaffold with complete monorepo directory structure
- `README.md` — flagship project overview with architecture ASCII diagram, quick start, and component table
- `CONTRIBUTING.md` — detailed contributor guide with Conventional Commits, branch naming, and PR process
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `SECURITY.md` — vulnerability reporting policy and security controls overview
- `ROADMAP.md` — 5-phase development roadmap with timelines and success criteria
- `CHANGELOG.md` — this file, tracking all notable changes

#### Architecture Documentation (`docs/`)
- `docs/prd/PRD.md` — Full Product Requirements Document: executive summary, functional requirements FR-1 through FR-8, non-functional requirements, success metrics
- `docs/architecture/SAD.md` — Software Architecture Document: 7-layer architecture, architectural principles AP-01 through AP-07, event architecture, security architecture
- `docs/architecture/SSD.md` — Software System Design Document: all agent component designs, Kafka topic contracts, database design, API design
- `docs/architecture/HLD.md` — High Level Design: executive overview, component specifications, agent communication model
- `docs/architecture/DDD.md` — Database Design Document: PostgreSQL schema (7 tables), TimescaleDB hypertables, Elasticsearch indexes, Redis key design
- `docs/architecture/LLD.md` — Low Level Design stub (Phase 2)

#### Architecture Decision Records (`docs/adr/`)
- `ADR-001` — Event-Driven Architecture (Accepted)
- `ADR-002` — Kafka as Event Backbone (Accepted)
- `ADR-003` — Kubernetes as Runtime Platform (Accepted)
- `ADR-004` — Multi-Agent Design (Accepted)
- `ADR-005` — ML-Based Anomaly Detection Strategy (Accepted)

#### C4 Architecture Diagrams (`docs/diagrams/`)
- `context.mmd` — C4 Context diagram (HECATE within its ecosystem)
- `container.mmd` — C4 Container diagram (all services and their relationships)
- `component.mmd` — C4 Component diagram (Detection Agent internals)
- `deployment.mmd` — Kubernetes namespace deployment topology

#### Governance (`docs/governance/`)
- `rbac.md` — Role-Based Access Control: 4 roles, permissions matrix, Kubernetes RBAC integration
- `policy-framework.md` — Policy engine schema, condition syntax, risk levels, example policies

#### Operations & Runbooks (`docs/operations/`, `docs/runbooks/`)
- `on-call.md` — On-call guide: escalation path, key metrics, common incidents
- `pod-restart-remediation.md` — Pod restart runbook: trigger conditions, automated steps, verification
- `scale-deployment.md` — Scaling runbook: HPA and manual scaling procedures
- `rollback-release.md` — Rollback runbook: ArgoCD and kubectl rollback procedures

#### ML & Security Docs (`docs/mlops/`, `docs/security/`)
- `docs/mlops/README.md` — Model inventory, training pipeline, drift detection, retraining triggers
- `docs/security/threat-model.md` — STRIDE analysis, threat actors, assets, mitigations
- `docs/security/security-controls.md` — Auth, RBAC, Vault, TLS, network policies, container security

#### Infrastructure Files
- `docker-compose.yml` — Full local dev stack: Kafka (KRaft), Kafka UI, PostgreSQL 16, Redis 7, Prometheus, Grafana, Jaeger, Elasticsearch 8, Kibana; all with health checks
- `Makefile` — Developer shortcuts: `dev`, `dev-down`, `lint`, `test`, `test-coverage`, `format`, `clean`, `k8s-apply`, and more
- `.env.example` — All environment variables documented with descriptions
- `.gitignore` — Comprehensive ignore rules for Python, Node.js, Terraform, Kubernetes, IDE, OS, secrets
- `pyproject.toml` — Ruff, mypy, pytest, and black configuration for the monorepo

---

## Links

- [Unreleased]: https://github.com/devmehta/hecate/compare/v0.1.0...HEAD
- [0.1.0]: https://github.com/devmehta/hecate/releases/tag/v0.1.0
