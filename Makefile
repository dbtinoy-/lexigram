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
CORE_SRC   := core/lexigram/src
TYPED_PKGS := packages/lexigram-audit packages/lexigram-auth packages/lexigram-cache packages/lexigram-events packages/lexigram-monitor packages/lexigram-notification packages/lexigram-queue packages/lexigram-search packages/lexigram-sql packages/lexigram-testing packages/lexigram-vector packages/lexigram-webhook packages/lexigram-workflow
WEB_DIR    := packages/lexigram-web

# Extension packages that pass mypy with their own per-package config.
# Add packages here one by one as they are cleaned up (see `make type-pkg`).
TYPED_PKGS := experimental/ai/lexigram-ai-agents experimental/ai/lexigram-ai-evaluation experimental/ai/lexigram-ai-feedback \
              experimental/ai/lexigram-ai-guard experimental/ai/lexigram-ai-llm experimental/ai/lexigram-ai-mcp \
              experimental/ai/lexigram-ai-memory \
              experimental/ai/lexigram-ai-observability experimental/ai/lexigram-ai-prompt \
              experimental/ai/lexigram-ai-relay-gateway experimental/ai/lexigram-ai-session \
              experimental/ai/lexigram-ai-skills experimental/ai/lexigram-ai-workers \
              packages/lexigram-audit packages/lexigram-events packages/lexigram-monitor \
              packages/lexigram-notification packages/lexigram-nosql packages/lexigram-queue \
              experimental/apps/lexigram-ui packages/lexigram-vector packages/lexigram-workflow \
              packages/lexigram-cache packages/lexigram-auth packages/lexigram-search \
              packages/lexigram-sql packages/lexigram-testing packages/lexigram-webhook

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

.PHONY: tailwind
tailwind:  ## Rebuild the static Tailwind CSS bundle (admin static/css/tailwind.css)
	TAILWIND_CACHE_DIR="$(CURDIR)/.cache/tailwindcss" ./tailwind/build.sh

.PHONY: lint
lint:  ## Run ruff check + format check (no writes)
	$(RUFF) check .
	$(RUFF) format --check .

.PHONY: lint-boundaries
lint-boundaries:  ## Run the namespace-aware import-linter contracts
	$(UV) run python tools/lint_imports.py

.PHONY: lint-fix
lint-fix:  ## Run ruff check + format (auto-fix)
	$(RUFF) check . --fix
	$(RUFF) format .

.PHONY: type
type:  ## Run mypy on core, lexigram-web and all TYPED_PKGS (each with its own pyproject config)
	$(MYPY) $(CORE_SRC)
	cd $(WEB_DIR) && $(MYPY) src/lexigram/web
	for p in $(TYPED_PKGS); do (cd $$p && $(MYPY) src) || exit 1; done

.PHONY: type-pkg
type-pkg:  ## Run mypy on one package with its own config: make type-pkg PKG=lexigram-web
	cd $(PKG) && $(MYPY) src

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
ci:  ## Full CI pipeline: lint + type-check + tests with coverage gate
	$(RUFF) check . \
	  && $(RUFF) format --check . \
	  && $(MYPY) $(CORE_SRC) \
	  && cd $(WEB_DIR) && $(MYPY) src/lexigram/web
	for p in $(TYPED_PKGS); do (cd $$p && $(MYPY) src) || exit 1; done
	$(PYTEST) --tb=short --cov-fail-under=80
	$(MAKE) check-demos

.PHONY: guard
guard:  ## Verify all dirty paths belong to this lane: make guard ALLOWED="path/a path/b"
	$(UV) run python dev/check_tree_guard.py --allow $(ALLOWED)

# ---------------------------------------------------------------------------
# Demos (living integration surfaces — gated like the framework)
# ---------------------------------------------------------------------------
# All four demos ship pytest suites and run from the repo root in the
# workspace env. Format and lint already cover demos/ via the root `ruff`
# invocations above. The llm-experiment harness imports opentelemetry,
# which lives in the `tooling` dependency group.
DEMO_PYTEST := $(UV) run --group tooling pytest
DEMO_TEST_DIRS := demos/event-driven-orders/tests demos/realtime-monitor/tests demos/llm-experiment/tests demos/resilient-rates/tests
DEMO_COMPILE_DIRS := demos/llm-experiment demos/event-driven-orders demos/realtime-monitor demos/resilient-rates

.PHONY: test-demos
test-demos:  ## Run demo test suites (event-driven-orders, realtime-monitor, llm-experiment, resilient-rates)
	$(DEMO_PYTEST) -q -m "not integration" --no-cov $(DEMO_TEST_DIRS)

.PHONY: verify-demos
verify-demos:  ## Compile-check demo entry points and scripts (incl. llm-experiment)
	$(UV) run python -m compileall -q $(DEMO_COMPILE_DIRS)

.PHONY: check-demos
check-demos: test-demos verify-demos  ## Demo gate: tests + compile checks

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

.PHONY: fmt
fmt:  ## Format code (no lint check)
	$(RUFF) format .

.PHONY: check
check:  ## Quick pre-commit check: lint + format + type (core + web + TYPED_PKGS, no tests)
	$(RUFF) check . && $(RUFF) format --check . && $(MYPY) $(CORE_SRC) && cd $(WEB_DIR) && $(MYPY) src/lexigram/web
	for p in $(TYPED_PKGS); do (cd $$p && $(MYPY) src) || exit 1; done

PKG ?= lexigram
.PHONY: test-pkg
test-pkg:  ## Run tests for a single package: make test-pkg PKG=lexigram-web
	$(PYTEST) $(PKG)/tests/ --tb=short -v

.PHONY: audit
audit:  ## Run dependency vulnerability scan
	$(UV) run pip-audit 2>/dev/null || $(UV) pip audit

.PHONY: catalog
catalog:  ## Regenerate docs/reference/REF_ERROR_CODES.md from source
	$(UV) run python dev/catalogs/generate_error_catalog.py

.PHONY: catalog-package
catalog-package:  ## Run all standalone catalog generators
	$(UV) run python dev/catalogs/generate_cli_commands_catalog.py
	$(UV) run python dev/catalogs/generate_env_vars_catalog.py
	$(UV) run python dev/catalogs/generate_error_catalog.py

REPRO_OUT := $(CURDIR)/.cache/eval-reproduce

.PHONY: eval-reproduce
eval-reproduce:  ## Re-run the seeded llm-experiment; fails if same-seed digests diverge
	$(UV) run python demos/llm-experiment/run_experiment.py --seed 7 --out $(REPRO_OUT)

version-check:  ## Compare local versions vs PyPI (exit 1 if bumps needed)
	$(UV) run python dev/check_version.py check

version-bump:  ## Show next version for PKG (add APPLY=--apply to write); all packages if PKG unset
	$(UV) run python dev/check_version.py bump $(if $(PKG),--pkg $(PKG),) $(APPLY)

version-bump-all:  ## Show next version for all packages
	$(UV) run python dev/check_version.py bump

# ---------------------------------------------------------------------------
# AUDIT File Generation (Test/Doc Audits)
# ---------------------------------------------------------------------------

# Public audit targets (write to docs/audit)
.PHONY: audit-overview
audit-overview:
	$(UV) run python -m dev.cli audit run overview

.PHONY: audit-integrations
audit-integrations:
	$(UV) run python -m dev.cli audit run integrations

.PHONY: audit-protocols
audit-protocols:
	$(UV) run python -m dev.cli audit run protocols

.PHONY: audit-security
audit-security:
	$(UV) run python -m dev.cli audit run security

.PHONY: audit-quality
audit-quality:
	$(UV) run python -m dev.cli audit run quality

.PHONY: audit-rules
audit-rules:
	$(UV) run python -m dev.cli audit run rules

.PHONY: audit-tests
audit-tests:
	$(UV) run python -m dev.cli audit run tests

.PHONY: audit-docs-links
audit-docs-links:
	$(UV) run python -m dev.cli audit run docs-links

.PHONY: audit-docs-claims
audit-docs-claims:
	$(UV) run python -m dev.cli audit run docs-claims

.PHONY: audit-docs-defaults
audit-docs-defaults:
	$(UV) run python -m dev.cli audit run docs-defaults

.PHONY: audit-docs-imports
audit-docs-imports:
	$(UV) run python -m dev.cli audit run docs-imports

.PHONY: audit-optional-imports
audit-optional-imports:
	$(UV) run python -m dev.cli audit run optional-imports

.PHONY: audit-dependencies
audit-dependencies:
	$(UV) run python -m dev.cli audit run dependencies

.PHONY: audit-files-dry
audit-package-dry:
	$(UV) run python -m dev.cli audit list

.PHONY: audit-package
audit-package: audit-overview audit-integrations audit-protocols audit-security audit-quality audit-rules audit-tests audit-optional-imports audit-docs-links audit-docs-imports audit-docs-claims audit-docs-defaults audit-dependencies scripts-audit-index
	@echo "All AUDIT files generated in docs/audit"

# All-packages audit targets (write to repo root)
audit-overview-all:
	$(UV) run python -m dev.cli audit run overview --all

audit-integrations-all:
	$(UV) run python -m dev.cli audit run integrations --all

audit-protocols-all:
	$(UV) run python -m dev.cli audit run protocols --all

audit-security-all:
	$(UV) run python -m dev.cli audit run security --all

audit-quality-all:
	$(UV) run python -m dev.cli audit run quality --all

audit-rules-all:
	$(UV) run python -m dev.cli audit run rules --all

audit-tests-all:
	$(UV) run python -m dev.cli audit run tests --all

audit-optional-imports-all:
	$(UV) run python -m dev.cli audit run optional-imports --all

audit-docs-links-all:
	$(UV) run python -m dev.cli audit run docs-links --all

audit-docs-claims-all:
	$(UV) run python -m dev.cli audit run docs-claims --all

audit-docs-defaults-all:
	$(UV) run python -m dev.cli audit run docs-defaults --all

audit-docs-imports-all:
	$(UV) run python -m dev.cli audit run docs-imports --all

audit-package-all: audit-overview-all audit-integrations-all audit-protocols-all audit-security-all audit-quality-all audit-rules-all audit-tests-all audit-optional-imports-all audit-docs-links-all audit-docs-imports-all audit-docs-claims-all audit-docs-defaults-all scripts-audit-index-all
	@echo "All AUDIT files generated at repo root"

.PHONY: scripts-audit
scripts-audit:
	$(UV) run python -m dev.cli audit run all

scripts-audit-all:
	$(UV) run python -m dev.cli audit run all --all

.PHONY: scripts-audit-index
scripts-audit-index:
	$(UV) run python -m dev.cli audit run index

scripts-audit-index-all:
	$(UV) run python -m dev.cli audit run index --all

.PHONY: scripts-audit-validate
scripts-audit-validate:
	$(UV) run python -m dev.cli audit validate

.PHONY: scripts-audit-rules
scripts-audit-rules:
	$(UV) run python -m dev.cli audit run rules
