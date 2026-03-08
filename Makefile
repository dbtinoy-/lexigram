# Lexigram Framework — Makefile
# Wraps the most common uv/pytest/ruff/mypy commands.

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
UV         := uv
PYTEST     := $(UV) run pytest
RUFF       := $(UV) run ruff
MYPY       := $(UV) run mypy
CORE_SRC   := lexigram/src/

# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

.PHONY: help
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev:  ## Install all workspace dependencies
	$(UV) sync

.PHONY: lint
lint:  ## Run ruff check + format check (no writes)
	$(RUFF) check .
	$(RUFF) format --check .

.PHONY: lint-fix
lint-fix:  ## Run ruff check + format (auto-fix)
	$(RUFF) check . --fix
	$(RUFF) format .

.PHONY: lint-boundaries
lint-boundaries:  ## Enforce import boundary contracts (namespace-aware import-linter)
	$(UV) run python tools/lint_imports.py

.PHONY: type
type:  ## Run mypy on the core package
	$(MYPY) $(CORE_SRC)

.PHONY: test
test:  ## Run the full test suite
	$(PYTEST) --tb=short -q

.PHONY: test-fast
test-fast:  ## Run tests, stop on first failure
	$(PYTEST) --tb=short -q -x

.PHONY: test-cov
test-cov:  ## Run tests with coverage report
	$(PYTEST) --tb=short --cov --cov-report=html --cov-fail-under=80

.PHONY: test-unit
test-unit:  ## Run only unit tests (exclude integration / e2e)
	$(PYTEST) --tb=short -q -m "not integration and not e2e"

.PHONY: ci
ci:  ## Full CI pipeline: lint + boundary-check + type-check + tests with coverage gate
	$(RUFF) check . \
	  && $(RUFF) format --check . \
	  && $(UV) run python tools/lint_imports.py \
	  && $(MYPY) $(CORE_SRC) \
	  && $(PYTEST) --tb=short --cov-fail-under=80

.PHONY: test-integration
test-integration:  ## Run integration tests (requires Docker Compose services)
	$(PYTEST) -m integration --tb=short -q

.PHONY: test-scenarios
test-scenarios:  ## Run cross-package scenario tests
	$(PYTEST) tests/integration/scenarios/ --tb=short -v

.PHONY: test-integration-all
test-integration-all: test-integration test-scenarios  ## Run all integration + scenario tests

.PHONY: test-integration-postgres
test-integration-postgres:  ## Run PostgreSQL integration tests
	$(PYTEST) -m requires_postgres --tb=short -v

.PHONY: test-integration-redis
test-integration-redis:  ## Run Redis integration tests
	$(PYTEST) -m requires_redis --tb=short -v

.PHONY: test-integration-kafka
test-integration-kafka:  ## Run Kafka integration tests
	$(PYTEST) -m requires_kafka --tb=short -v

# ---------------------------------------------------------------------------
# Integration testing (Docker-backed)
# ---------------------------------------------------------------------------
DOCKER_COMPOSE := docker-compose
COMPOSE_FILE   := docker-compose.test.yml

.PHONY: integration-deps
integration-deps:  ## Start integration test services (PostgreSQL, Redis, Kafka, …)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d --wait
	@echo "Integration services ready."

.PHONY: integration-stop
integration-stop:  ## Stop and remove integration test services + volumes
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v --remove-orphans
	@echo "Integration services stopped."

.PHONY: integration-test
integration-test:  ## Run ALL integration tests (starts deps if needed)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d --wait
	$(PYTEST) -m integration --tb=short -q
	@echo "Integration tests complete."

.PHONY: integration-test-postgres
integration-test-postgres:  ## Run only requires_postgres integration tests
	$(PYTEST) -m "integration and requires_postgres" --tb=short -v

.PHONY: integration-test-redis
integration-test-redis:  ## Run only requires_redis integration tests
	$(PYTEST) -m "integration and requires_redis" --tb=short -v

.PHONY: integration-test-kafka
integration-test-kafka:  ## Run only requires_kafka integration tests (replaces old target)
	$(PYTEST) -m "integration and requires_kafka" --tb=short -v

.PHONY: integration-test-mongo
integration-test-mongo:  ## Run only requires_mongodb integration tests
	$(PYTEST) -m "integration and requires_mongodb" --tb=short -v

.PHONY: integration-test-search
integration-test-search:  ## Run only requires_elasticsearch integration tests
	$(PYTEST) -m "integration and requires_elasticsearch" --tb=short -v

.PHONY: integration-test-storage
integration-test-storage:  ## Run only requires_minio integration tests
	$(PYTEST) -m "integration and requires_minio" --tb=short -v

.PHONY: integration-test-vector
integration-test-vector:  ## Run only requires_qdrant integration tests
	$(PYTEST) -m "integration and requires_qdrant" --tb=short -v

.PHONY: integration-test-scenarios
integration-test-scenarios:  ## Run cross-package scenario tests
	$(PYTEST) -m "integration and scenario" --tb=short -v

.PHONY: integration-logs
integration-logs:  ## Tail logs from integration test services
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f

.PHONY: clean
clean:  ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name "API.md" -delete 2>/dev/null || true
	find . -name "INDEX.md" -delete 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	@echo "Clean complete."

.PHONY: docs
docs:  ## Regenerate API surface files
	$(UV) run python tools/generate_package_api.py -s 25000

.PHONY: fmt
fmt:  ## Format code (no lint check)
	$(RUFF) format .

.PHONY: check
check:  ## Quick pre-commit check: lint + format + type (no tests)
	$(RUFF) check . && $(RUFF) format --check . && $(MYPY) $(CORE_SRC)

PKG ?= lexigram
.PHONY: test-pkg
test-pkg:  ## Run tests for a single package: make test-pkg PKG=lexigram-web
	$(PYTEST) $(PKG)/tests/ --tb=short -v

.PHONY: audit
audit:  ## Run dependency vulnerability scan
	$(UV) run pip-audit 2>/dev/null || $(UV) pip audit

.PHONY: catalog
catalog:  ## Regenerate docs/lexigram-docs/reference/REF_ERROR_CODES.md from source
	$(UV) run python scripts/catalogs/generate_error_catalog.py

.PHONY: catalog-package
catalog-package:  ## Run all standalone catalog generators
	$(UV) run python scripts/catalogs/generate_cli_commands_catalog.py
	$(UV) run python scripts/catalogs/generate_env_vars_catalog.py
	$(UV) run python scripts/catalogs/generate_error_catalog.py

# ---------------------------------------------------------------------------
# Public mirror publish
# ---------------------------------------------------------------------------

.PHONY: publish-framework
publish-framework:  ## Push framework packages to public mirror
	COMMIT_MSG="$(m)" bash tools/publish_public.sh --push

.PHONY: publish-experimental
publish-experimental:  ## Push experimental packages (cli, ui, admin) to *-experimental repos
	COMMIT_MSG="$(m)" bash tools/publish_public.sh --experimental --push

.PHONY: publish-all
publish-all:  ## Push both framework and experimental packages
	COMMIT_MSG="$(m)" bash tools/publish_public.sh --push --experimental

.PHONY: publish-reset
publish-reset:  ## Force-reset main mirror history (rare)
	bash tools/publish_public.sh --reset --push

.PHONY: publish-dry-framework
publish-dry-framework:  ## Dry run — framework packages only, no push
	bash tools/publish_public.sh

# ---------------------------------------------------------------------------
# Version check & bump (git ↔ PyPI sync)
# ---------------------------------------------------------------------------

.PHONY: version-check
version-check:  ## Compare local versions vs PyPI (exit 1 if bumps needed)
	$(UV) run python scripts/check_version.py check

.PHONY: version-bump
version-bump:  ## Show next version for PKG (add APPLY=--apply to write); all packages if PKG unset
	$(UV) run python scripts/check_version.py bump $(if $(PKG),--pkg $(PKG),) $(APPLY)

.PHONY: version-bump-all
version-bump-all:  ## Show next version for all packages
	$(UV) run python scripts/check_version.py bump

.PHONY: publish-dry-experimental
publish-dry-experimental:  ## Dry run — experimental packages only, no push
	COMMIT_MSG="$(m)" bash tools/publish_public.sh --experimental

.PHONY: publish-dry-all
publish-dry-all:  ## Dry run — both framework and experimental, no push
	COMMIT_MSG="$(m)" bash tools/publish_public.sh --experimental

# ---------------------------------------------------------------------------
# AUDIT File Generation (Test/Doc Audits)
# ---------------------------------------------------------------------------

# Public audit targets (write to docs/lexigram-docs/audit)
.PHONY: audit-overview
audit-overview:
	$(UV) run python -m scripts.cli audit run overview

.PHONY: audit-integrations
audit-integrations:
	$(UV) run python -m scripts.cli audit run integrations

.PHONY: audit-protocols
audit-protocols:
	$(UV) run python -m scripts.cli audit run protocols

.PHONY: audit-security
audit-security:
	$(UV) run python -m scripts.cli audit run security

.PHONY: audit-quality
audit-quality:
	$(UV) run python -m scripts.cli audit run quality

.PHONY: audit-rules
audit-rules:
	$(UV) run python -m scripts.cli audit run rules

.PHONY: audit-tests
audit-tests:
	$(UV) run python -m scripts.cli audit run tests

.PHONY: audit-docs-links
audit-docs-links:
	$(UV) run python -m scripts.cli audit run docs-links

.PHONY: audit-optional-imports
audit-optional-imports:
	$(UV) run python -m scripts.cli audit run optional-imports

.PHONY: audit-files-dry
audit-package-dry:
	$(UV) run python -m scripts.cli audit list

.PHONY: audit-package
audit-package: audit-overview audit-integrations audit-protocols audit-security audit-quality audit-rules audit-tests audit-optional-imports audit-docs-links scripts-audit-index
	@echo "All AUDIT files generated in docs/lexigram-docs/audit"

# All-packages audit targets (write to repo root)
.PHONY: audit-overview-all
audit-overview-all:
	$(UV) run python -m scripts.cli audit run overview --all

.PHONY: audit-integrations-all
audit-integrations-all:
	$(UV) run python -m scripts.cli audit run integrations --all

.PHONY: audit-protocols-all
audit-protocols-all:
	$(UV) run python -m scripts.cli audit run protocols --all

.PHONY: audit-security-all
audit-security-all:
	$(UV) run python -m scripts.cli audit run security --all

.PHONY: audit-quality-all
audit-quality-all:
	$(UV) run python -m scripts.cli audit run quality --all

.PHONY: audit-rules-all
audit-rules-all:
	$(UV) run python -m scripts.cli audit run rules --all

.PHONY: audit-tests-all
audit-tests-all:
	$(UV) run python -m scripts.cli audit run tests --all

.PHONY: audit-optional-imports-all
audit-optional-imports-all:
	$(UV) run python -m scripts.cli audit run optional-imports --all

.PHONY: audit-docs-links-all
audit-docs-links-all:
	$(UV) run python -m scripts.cli audit run docs-links --all

.PHONY: audit-package-all
audit-package-all: audit-overview-all audit-integrations-all audit-protocols-all audit-security-all audit-quality-all audit-rules-all audit-tests-all audit-optional-imports-all audit-docs-links-all scripts-audit-index-all
	@echo "All AUDIT files generated at repo root"

.PHONY: scripts-audit
scripts-audit:
	$(UV) run python -m scripts.cli audit run all

.PHONY: scripts-audit-all
scripts-audit-all:
	$(UV) run python -m scripts.cli audit run all --all

.PHONY: scripts-audit-index
scripts-audit-index:
	$(UV) run python -m scripts.cli audit run index

.PHONY: scripts-audit-index-all
scripts-audit-index-all:
	$(UV) run python -m scripts.cli audit run index --all

.PHONY: scripts-audit-validate
scripts-audit-validate:
	$(UV) run python -m scripts.cli audit validate

.PHONY: scripts-audit-rules
scripts-audit-rules:
	$(UV) run python -m scripts.cli audit run rules
