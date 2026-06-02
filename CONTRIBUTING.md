# Contributing to HECATE

Thank you for your interest in contributing to **HECATE — Heuristic Engine for Cloud Automation, Telemetry & Execution**! This document provides all the information you need to contribute effectively.

We welcome contributions of all kinds: bug reports, feature suggestions, documentation improvements, and code contributions.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
  - [Reporting Issues](#reporting-issues)
  - [Suggesting Features](#suggesting-features)
  - [Submitting Pull Requests](#submitting-pull-requests)
- [Development Setup](#development-setup)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [Architecture Decision Records](#architecture-decision-records)

---

## Code of Conduct

This project and everyone participating in it is governed by the [HECATE Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainer.

---

## How to Contribute

### Reporting Issues

Before submitting an issue, please:

1. **Search existing issues** to ensure it hasn't already been reported.
2. **Check the documentation** and runbooks in `docs/runbooks/` — your question may already be answered.
3. **Use the latest version** of the code from `main`.

When opening an issue, select the appropriate template:
- **Bug Report**: For unexpected behavior or crashes.
- **Feature Request**: For new capabilities or improvements.
- **Documentation**: For gaps or errors in docs.

Include as much context as possible:
- HECATE version (`HECATE_VERSION` from `.env`)
- Environment (local Docker, Kubernetes cluster, cloud provider)
- Relevant logs (`docker-compose logs <service>` or kubectl logs)
- Steps to reproduce

### Suggesting Features

Feature suggestions are tracked as GitHub Issues with the `enhancement` label. For significant architectural changes, please open a discussion first and reference or create an ADR in `docs/adr/`.

### Submitting Pull Requests

1. **Fork** the repository and **clone** your fork.
2. **Create a branch** following our [naming convention](#branch-naming-convention).
3. **Make your changes** with tests, documentation, and lint compliance.
4. **Push** your branch and open a PR against `main`.
5. **Fill out the PR template** completely.
6. **Request a review** from at least one maintainer.

---

## Development Setup

### 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Use `pyenv` or `asdf` to manage versions |
| Docker Desktop | 24.x+ | With Docker Compose v2 |
| Node.js | 20 LTS | For dashboard frontend |
| `make` | Any | For convenience targets |
| `kubectl` | 1.28+ | For Kubernetes interaction |
| `pre-commit` | Latest | For git hooks |

### 2. Fork and Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/hecate.git
cd hecate

# Add upstream remote
git remote add upstream https://github.com/devmehta/hecate.git
```

### 3. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows PowerShell
```

### 4. Install Dependencies

```bash
make install          # Install all Python agent dependencies
make dashboard-install  # Install frontend Node.js dependencies
pip install pre-commit
pre-commit install    # Install git hooks
```

### 5. Set Up Environment

```bash
cp .env.example .env
# Edit .env with local values (the defaults work for Docker Compose)
```

### 6. Start the Infrastructure

```bash
make dev   # Starts Kafka, PostgreSQL, Redis, Prometheus, Grafana, Jaeger, Elasticsearch
```

### 7. Run the Tests

```bash
make test
make test-coverage
```

### 8. Verify the Setup

```bash
make lint   # Should produce no errors
```

---

## Branch Naming Convention

Branch names must follow this pattern: `<type>/<short-description>`

| Type | Purpose | Example |
|------|---------|---------|
| `feature/` | New functionality | `feature/isolation-forest-detection` |
| `fix/` | Bug fix | `fix/kafka-consumer-reconnect` |
| `docs/` | Documentation only | `docs/rca-agent-runbook` |
| `chore/` | Tooling, CI, dependencies | `chore/upgrade-kafka-3.7` |
| `refactor/` | Code restructuring (no behavior change) | `refactor/decision-engine-cleanup` |
| `test/` | Test additions or fixes | `test/monitoring-agent-unit-tests` |
| `perf/` | Performance improvements | `perf/anomaly-scorer-optimization` |

Branch names must use lowercase and hyphens only. No underscores or uppercase.

---

## Commit Message Format

HECATE uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

### Format

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, missing semicolons, etc. (no logic change) |
| `refactor` | Code restructuring (no new feature, no bug fix) |
| `test` | Adding or fixing tests |
| `chore` | Build process, dependency updates, tooling |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration changes |

### Scopes

Use the component name as scope:
`monitoring`, `detection`, `rca`, `decision`, `remediation`, `learning`, `reporting`, `dashboard`, `kafka`, `shared`, `infra`, `docs`, `ci`

### Examples

```
feat(detection): add Isolation Forest anomaly detection model

Implement scikit-learn IsolationForest with configurable contamination
factor. Model is loaded from MODEL_PATH env var on startup. Falls back
to rule-based detection if model is unavailable.

Closes #42
```

```
fix(kafka): handle consumer rebalance exception gracefully

Previously, a rebalance during message processing caused the consumer
to crash and not restart. Now it logs the exception and re-initializes
the consumer with exponential backoff.

Fixes #87
```

```
docs(adr): add ADR-006 for TimescaleDB selection

Justifies choosing TimescaleDB over InfluxDB and VictoriaMetrics
for time-series storage.
```

### Breaking Changes

For breaking API or event schema changes, add `!` after the type/scope and include a `BREAKING CHANGE:` footer:

```
feat(schemas)!: rename anomaly_score to confidence_score in anomaly event

BREAKING CHANGE: All consumers of anomaly-topic must be updated to use
the new field name `confidence_score`. The old field `anomaly_score`
is removed.
```

---

## Pull Request Process

### Before Opening a PR

- [ ] Your branch is up to date with `upstream/main`
- [ ] All tests pass: `make test`
- [ ] No lint errors: `make lint`
- [ ] Code is formatted: `make format`
- [ ] New code has appropriate unit tests (≥80% coverage on changed files)
- [ ] Relevant documentation is updated
- [ ] CHANGELOG.md is updated under `[Unreleased]`

### PR Title

PR titles must also follow Conventional Commits format:
```
feat(detection): add LSTM-based time series anomaly detection
```

### Review Requirements

- All PRs require **at least 1 approving review** from a maintainer.
- All CI checks must pass (lint, test, build).
- PRs that change Kafka event schemas must include a migration strategy or schema backward-compatibility proof.
- PRs that change the database schema must include an Alembic migration.
- PRs that add new agents must include unit tests, a runbook entry, and an update to the architecture diagram.

### Merge Strategy

- All PRs are merged using **Squash and Merge** to keep the `main` branch history clean.
- The squash commit message must follow Conventional Commits format.

---

## Code Style

### Python

| Tool | Config | Purpose |
|------|--------|---------|
| `ruff` | `pyproject.toml` | Linting (replaces flake8, isort, pyupgrade) |
| `mypy` | `pyproject.toml` | Static type checking |
| `black` | `pyproject.toml` | Code formatting (via ruff-format) |

Key style rules:
- Line length: **100 characters**
- Use type annotations on all public functions and methods
- Use `Pydantic` models for all data structures crossing service boundaries
- Follow `snake_case` for variables and functions, `PascalCase` for classes
- Use `pathlib.Path` instead of `os.path`
- Use `asyncio` for all I/O-bound operations (all agents are async)
- No `print()` — use the configured logger (`structlog` or `logging`)

### TypeScript (Dashboard Frontend)

- Use `ESLint` with the project's `.eslintrc` config
- Use `Prettier` for formatting
- Use `strict` TypeScript mode
- Prefer `interface` over `type` for object shapes
- All React components use function components with hooks; no class components

---

## Testing Requirements

### Unit Tests

- Location: `tests/unit/<agent-name>/`
- Coverage requirement: **≥70% overall**, **≥80% on changed files**
- Use `pytest` with `pytest-asyncio` for async tests
- Mock external dependencies (Kafka, Postgres, Kubernetes API) using `pytest-mock` or `unittest.mock`
- Tests must be deterministic — no random seeds without being fixed

### Integration Tests

- Location: `tests/integration/`
- Require Docker Compose to be running (`make dev`)
- Test full pipelines end-to-end (e.g., publish a metric to Kafka, verify anomaly is produced)
- Run with: `pytest tests/integration/ -v --integration`

### Test File Naming

- `test_<module>.py` — unit test
- `test_<pipeline>_integration.py` — integration test

### Example Test Structure

```python
# tests/unit/detection/test_anomaly_scorer.py
import pytest
from agents.detection.anomaly_scorer import AnomalyScorer, MetricPoint

class TestAnomalyScorer:
    def test_high_cpu_triggers_anomaly(self):
        scorer = AnomalyScorer(cpu_threshold=85.0)
        point = MetricPoint(metric="cpu_usage", value=92.5, namespace="default", pod="api-xyz")
        result = scorer.evaluate(point)
        assert result.is_anomaly is True
        assert result.confidence_score >= 0.8
```

---

## Documentation Requirements

- All new agents must have a `README.md` in their directory explaining purpose, inputs, outputs, and configuration.
- All new Kafka topics must have a JSON Schema in `schemas/`.
- All significant architectural decisions must have an ADR in `docs/adr/`.
- All new runbook scenarios must be documented in `docs/runbooks/`.
- Public Python functions and classes must have docstrings in Google style:

```python
def evaluate_anomaly(metric: MetricPoint, threshold: float) -> AnomalyResult:
    """Evaluate whether a metric point constitutes an anomaly.

    Args:
        metric: The metric data point to evaluate.
        threshold: The score threshold above which the point is anomalous.

    Returns:
        An AnomalyResult containing the score and classification.

    Raises:
        ValueError: If threshold is not between 0 and 1.
    """
```

---

## Architecture Decision Records

For any decision that has significant long-term architectural impact:

1. Create a new file: `docs/adr/ADR-<NNN>-<short-title>.md`
2. Follow the existing ADR template (see `docs/adr/ADR-001-event-driven-architecture.md`)
3. Set status to `Proposed`
4. Open a PR and tag it `adr`
5. Status will be updated to `Accepted` or `Rejected` after review

---

*Thank you for helping build HECATE! Every contribution, however small, moves us closer to autonomous cloud reliability.*
