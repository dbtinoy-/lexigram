# SQL Repository Demo

Demonstrates the **Lexigram provider pattern** — in-memory stores, CRUD operations,
and the DI lifecycle.  Demonstrates how to wire services into the container
and expose them over HTTP with a clean composition root.

## What you'll learn

1. **Provider pattern** — `register()` declares bindings, `boot()` wires them
2. **Controller pattern** — thin HTTP adapters that delegate to services
3. **Config model** — typed dataclass with `BaseConfig` + `Field()` defaults
4. **Test bootstrap** — real composition root, no mocks, `httpx.ASGITransport`

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — web server, CSRF, demo settings |
| 2 | `src/taskapp/app.py` | Composition root — `build_modules()` + `build_providers()` |
| 3 | `src/taskapp/di/provider.py` | Provider lifecycle — `register()`, `boot()`, `health_check()` |
| 4 | `src/taskapp/config.py` | Config model — `BaseConfig` + `Field()` with descriptions |
| 5 | `src/taskapp/controllers/api.py` | HTTP surface — thin controller adapters, CRUD endpoints |
| 6 | `tests/` | Real composition root, no mocks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      application.yaml                           │
│  web: server/host/port, security/csrf/enabled                  │
│  task_app: project_name                                        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│  build_modules()  → [WebModule.configure(controllers=[...])]    │
│  build_providers() → [TaskProvider()]                           │
│  create_app()     → Application(name="sql-repository")         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      provider.py                                │
│  register(): container.singleton(TaskAppConfig, instance=cfg)  │
│  boot():     resolve config → create stores → bind controller   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     controllers/api.py                           │
│  prefix = "/api/tasks"                                          │
│  POST/GET/DELETE users, projects, tasks                         │
│  PUT /tasks/{id}/status                                        │
└─────────────────────────────────────────────────────────────────┘
```

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

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/tasks/users` | Create a user |
| `GET` | `/api/tasks/users` | List all users |
| `GET` | `/api/tasks/users/{id}` | Get a user by ID |
| `DELETE` | `/api/tasks/users/{id}` | Delete a user |
| `POST` | `/api/tasks/projects` | Create a project |
| `GET` | `/api/tasks/projects` | List all projects |
| `GET` | `/api/tasks/projects/{id}` | Get a project by ID |
| `DELETE` | `/api/tasks/projects/{id}` | Delete a project |
| `POST` | `/api/tasks/tasks` | Create a task |
| `GET` | `/api/tasks/tasks` | List all tasks |
| `GET` | `/api/tasks/tasks/{id}` | Get a task by ID |
| `PUT` | `/api/tasks/tasks/{id}/status` | Update task status |
| `DELETE` | `/api/tasks/tasks/{id}` | Delete a task |
