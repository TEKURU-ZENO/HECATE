# =============================================================================
# HECATE — Developer Makefile
# Provides shortcuts for common development tasks.
# Usage: make <target>
# =============================================================================

.DEFAULT_GOAL := help
.PHONY: help dev dev-down dev-logs install lint test test-coverage build clean \
        dashboard-dev dashboard-install docs-serve k8s-apply format migrate

PYTHON := python3
PIP    := pip3
NPM    := npm
DOCKER := docker
DC     := docker compose
KUBECTL := kubectl

# ANSI color codes
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

# =============================================================================
# HELP
# =============================================================================

help: ## Show this help message
	@echo ""
	@echo "  $(CYAN)HECATE — Developer Makefile$(RESET)"
	@echo "  $(YELLOW)Usage: make <target>$(RESET)"
	@echo ""
	@echo "  $(GREEN)Infrastructure$(RESET)"
	@grep -E '^(dev|dev-down|dev-logs|build):.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    $(CYAN)%-24s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "  $(GREEN)Development$(RESET)"
	@grep -E '^(install|lint|format|test|test-coverage|clean|migrate):.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    $(CYAN)%-24s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "  $(GREEN)Dashboard$(RESET)"
	@grep -E '^(dashboard-dev|dashboard-install):.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    $(CYAN)%-24s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "  $(GREEN)Docs & Kubernetes$(RESET)"
	@grep -E '^(docs-serve|k8s-apply):.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    $(CYAN)%-24s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# INFRASTRUCTURE — Docker Compose
# =============================================================================

dev: ## Start the full local development stack (Docker Compose)
	@echo "$(GREEN)Starting HECATE local dev stack...$(RESET)"
	$(DC) up -d
	@echo "$(GREEN)Stack is up. Services:$(RESET)"
	@echo "  Kafka UI   → http://localhost:8080"
	@echo "  Prometheus → http://localhost:9090"
	@echo "  Grafana    → http://localhost:3000"
	@echo "  Jaeger     → http://localhost:16686"
	@echo "  Kibana     → http://localhost:5601"
	@echo "  Dashboard  → http://localhost:8000"

dev-down: ## Stop and remove all local dev containers
	@echo "$(YELLOW)Stopping HECATE local dev stack...$(RESET)"
	$(DC) down

dev-logs: ## Follow logs from all Docker Compose services
	$(DC) logs -f

build: ## Build all Docker images (application services)
	@echo "$(GREEN)Building HECATE Docker images...$(RESET)"
	$(DC) build --no-cache

# =============================================================================
# DEVELOPMENT — Python
# =============================================================================

install: ## Install all Python dependencies (all agents + shared)
	@echo "$(GREEN)Installing Python dependencies...$(RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install -r agents/monitoring/requirements.txt
	$(PIP) install -r agents/detection/requirements.txt
	$(PIP) install -r agents/rca/requirements.txt
	$(PIP) install -r agents/decision/requirements.txt
	$(PIP) install -r agents/remediation/requirements.txt
	$(PIP) install -r agents/learning/requirements.txt
	$(PIP) install -r agents/reporting/requirements.txt
	$(PIP) install -r dashboard/api/requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)All dependencies installed.$(RESET)"

format: ## Format all Python code using ruff
	@echo "$(GREEN)Formatting Python code with ruff...$(RESET)"
	ruff format agents/ shared/ dashboard/api/ tests/
	@echo "$(GREEN)Formatting complete.$(RESET)"

lint: ## Run ruff linter and mypy type checker
	@echo "$(GREEN)Running ruff linter...$(RESET)"
	ruff check agents/ shared/ dashboard/api/ tests/ --fix
	@echo "$(GREEN)Running mypy type checker...$(RESET)"
	mypy agents/ shared/ dashboard/api/ --ignore-missing-imports
	@echo "$(GREEN)All checks passed.$(RESET)"

test: ## Run the full test suite with pytest
	@echo "$(GREEN)Running test suite...$(RESET)"
	pytest tests/ -v --tb=short

test-coverage: ## Run tests with HTML coverage report
	@echo "$(GREEN)Running tests with coverage...$(RESET)"
	pytest tests/ -v --cov=agents --cov=shared --cov=dashboard \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=70
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(RESET)"

migrate: ## Run database migrations (Alembic)
	@echo "$(GREEN)Running database migrations...$(RESET)"
	alembic upgrade head
	@echo "$(GREEN)Migrations complete.$(RESET)"

clean: ## Remove all build artifacts and cache files
	@echo "$(YELLOW)Cleaning up build artifacts...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete.$(RESET)"

# =============================================================================
# DASHBOARD
# =============================================================================

dashboard-install: ## Install frontend Node.js dependencies
	@echo "$(GREEN)Installing frontend dependencies...$(RESET)"
	cd dashboard/frontend && $(NPM) install
	@echo "$(GREEN)Frontend dependencies installed.$(RESET)"

dashboard-dev: ## Start the frontend dev server (Vite)
	@echo "$(GREEN)Starting HECATE Dashboard dev server...$(RESET)"
	cd dashboard/frontend && $(NPM) run dev

# =============================================================================
# DOCS
# =============================================================================

docs-serve: ## Serve documentation locally with MkDocs
	@echo "$(GREEN)Starting MkDocs documentation server...$(RESET)"
	mkdocs serve --dev-addr 127.0.0.1:8001

# =============================================================================
# KUBERNETES
# =============================================================================

k8s-apply: ## Apply Kubernetes manifests (Kustomize)
	@echo "$(GREEN)Applying Kubernetes manifests...$(RESET)"
	$(KUBECTL) apply -k infrastructure/kubernetes/overlays/dev
	@echo "$(GREEN)Manifests applied.$(RESET)"

k8s-status: ## Show status of HECATE pods in the cluster
	$(KUBECTL) get pods -n hecate-system
	$(KUBECTL) get pods -n hecate-agents
