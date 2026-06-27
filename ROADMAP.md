# HECATE Platform Roadmap

## Phase 1: Foundation & Scaffold (Current)
* Setup monorepo structure
* Complete all architecture design, system design, and contracts
* Local dev environment via Docker Compose
* Dashboard skeleton and React application routing

## Phase 2: Core Event Flow & Basic Remediation (Session 2)
* Prometheus metric collector (Monitoring Agent)
* Ingestion API (Telemetry Service)
* Basic rule-based anomaly detection
* Restart-pod remediation execution

## Phase 3: ML-driven Intelligence (Session 3)
* Isolation Forest for unsupervised anomaly detection
* LSTM for time-series forecasting
* RCA Graph traversal implementation

## Phase 4: Dynamic Policy & Governance (Session 4)
* Policy engine with DSL condition evaluation
* RBAC controls integration in Dashboard API
* Manual approval gates for high-risk remediations

## Phase 5: Autonomous Self-Healing & MLOps (Session 5)
* Learning agent for reinforcement learning optimization
* Model drift detection and automated retraining
* Chaos testing validation at scale

## Phase 10: HECATE v2.0 — Autonomous Infrastructure Simulation & Planning (Session 10)
* Standalone `digital-twin-service` (port 8006) for sequence simulation & self-calibration
* OPA-like Declarative Policy Service and post-simulation Decision risk engine
* Execution Validator (topology freshness & liveness protection gate)
* Recommendation Agent Q-value optimization via Temporal Difference (TD) learning
* React Twin Explorer Dashboard with Reality vs Prediction error metrics

## Phase 11: Production-Grade Reliability & Controlled Evaluation Harness (v2.0.5)
* Modular evaluation framework (`evaluation/`) separating context, metrics, and reports
* Standardized metrics registry and chaos scenario failure injectors
* Welch's t-test ($p < 0.05$), Cohen's d, and bootstrap significance verification
* Interactive dashboard reports (`evaluation.html`) and LaTeX/SVG exports
* CLI comparator tool for versioned results delta profiling