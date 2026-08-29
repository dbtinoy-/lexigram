# Tests

This directory contains the test suite for the Lexigram framework.

## Structure

```text
tests/
├── dev/                    # Developer tooling tests (generators, audits, CLI checks)
├── integration/
│   ├── scenarios/          # Cross-package scenario apps (in-memory, no live services)
│   │   ├── conftest.py     # Scenario fixtures and factory stubs
│   │   ├── scenario_apps.py
│   │   ├── relay_fakes/    # Stub implementations for relay system tests
│   │   ├── test_audit_trail.py
│   │   ├── test_events_sql.py
│   │   ├── test_tasks_queue.py
│   │   ├── test_tenancy_isolation.py
│   │   ├── test_web_auth_session.py
│   │   ├── test_web_cache_sql.py
│   │   └── test_web_sql_crud.py
│   └── extension_tests/    # Per-package integration tests
├── test_env_audit_non_config_sources.py
├── test_workspace_config.py
├── docker-compose.yml      # PostgreSQL, Redis, Kafka, MinIO for integration
└── wait-for-services.sh
```

## Quick Start

```bash
# Unit tests only (default — no external services needed)
uv run pytest

# Explicit form (equivalent)
uv run pytest -m "not integration"

# Integration tests (requires docker compose up -d)
uv run pytest -m integration
```

## Running Specific Tests

```bash
# Scoped runs
uv run pytest tests/dev/test_registry.py -v
uv run pytest tests/integration/scenarios/ -v
uv run pytest -k "test_user"

# One package's tests
uv run pytest packages/lexigram-web/tests/

# One test
uv run pytest tests/dev/test_registry.py::test_audit_registry_contains_expected_generators -v
```

## Scenario Suite

The `tests/integration/scenarios/` directory contains cross-package integration tests
that run **entirely in-memory** — no live Postgres, Redis, or Docker required. Each
scenario boots a minimal Lexigram application configured for a specific package
composition (CRUD, events, web auth, audit, cache, tasks, tenancy).

These are integration-marked and run only with `-m integration` or explicitly
navigated via path:

```bash
uv run pytest tests/integration/scenarios/ -v
```

## Docker Services

For tests requiring external infrastructure:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 15432 | Database tests (lexigram-sql) |
| Redis | 16379 | Cache tests (lexigram-cache) |
| Kafka | 19092 | Queue tests (lexigram-queue) |
| MinIO | 19000 | Storage tests (lexigram-storage) |

```bash
docker compose up -d
uv run pytest -m integration
docker compose down -v
```

## Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.integration` | Requires external services |
| `@pytest.mark.requires_postgres` | Skip unless PostgreSQL is available |
| `@pytest.mark.requires_redis` | Skip unless Redis is available |

```bash
uv run pytest -m requires_postgres
uv run pytest -m "requires_postgres or requires_redis"
```

## Coverage

```bash
uv run pytest --cov --cov-report=html
uv run pytest --cov-fail-under=80
```
