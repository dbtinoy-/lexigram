# SQL Repository Demo

Teaches `lexigram-sql` — repository CRUD, unit-of-work, domain events, and
the DI lifecycle with SQLite.

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — database URL, pool settings |
| 2 | `src/taskapp/app.py` | Composition root — module wiring |
| 3 | `src/taskapp/di/provider.py` | Provider lifecycle — register, boot, shutdown |
| 4 | `src/taskapp/domain.py` | Domain models — immutable value objects |
| 5 | `src/taskapp/repository/` | Repository pattern — CRUD with SQLRepository |
| 6 | `src/taskapp/services/` | Business logic — Result[T, E] error handling |
| 7 | `src/taskapp/controllers/api.py` | HTTP surface — thin controller adapters |
| 8 | `tests/` | Real composition root, no mocks |

## Quick start

```bash
cd demos/sql-repository
uv run python -m taskapp
```

## Run tests

```bash
cd demos/sql-repository
uv run pytest tests/ -v
```
