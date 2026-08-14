---
title: lexigram-cli Guide
description: Full walkthrough of project scaffolding, code generation, database management, and runtime inspection
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-web` | Yes | Web UI support |

## The Problem `lexigram-cli` Solves

Building a Lexigram application involves repeated setup: project scaffolding, code generation, database migrations, and runtime inspection. `lexigram-cli` automates these tasks through a single `lexigram` command, using a **contributor-based plugin system** where packages extend the CLI via `lexigram.cli.contributors` entry points.

**Mental model:** Think of `lexigram-cli` as the framework's toolbox — one command to create, build, run, and introspect your application.

---

## Core Concepts

- **Command groups** — commands are organized as sub-Typer apps (`new`, `run`, `dev`, `db`, `gen`, `inspect`, `shell`, etc.)
- **Contributors** — packages advertise commands, generators, health checks, shell context, and hooks via `lexigram.cli.contributors`; discovered at import with automatic conflict resolution
- **CLIContext** — per-invocation shared state holding config, output mode (Rich/JSON/Quiet), and flags
- **`OutputManager`** — centralized output with support for Rich formatting, JSON serialization, and debug modes

---

## Full Command Walkthrough

### Scaffolding (`new`, `add`)

```bash
# Create a new project from a template
lexigram new project my-app --template web-api -d ./projects

# Create a project interactively
lexigram new project my-app -i

# Scaffold a new lexigram-* extension package
lexigram new package my-feature

# Add a provider to an existing project
lexigram add web
lexigram add sql
```

Available templates: `web-api`, `full`, `api`.

### Dev Server (`run`, `dev`)

```bash
# Auto-detect create_app() and start the server
lexigram run

# Explicit entry point
lexigram run my_app.app:create_app --port 9000 --no-reload

# Development server with hot-reload
lexigram dev --entry src/main.py --port 8000 --env development

# Use a specific server backend
lexigram run --server granian

# Run with an MCP SSE server alongside
lexigram run --mcp-port 8080
```

The CLI auto-detects the server backend, preferring Granian → Uvicorn → Hypercorn based on availability.

### Database Management (`db`)

```bash
# Create/upgrade a database and generate an initial migration
lexigram db init

# Auto-generate a migration from schema changes
lexigram db migrate -m "add email to users"

# Apply pending migrations
lexigram db upgrade

# Rollback the last migration
lexigram db rollback

# View migration status
lexigram db status

# Seed test data
lexigram db seed

# View migration history
lexigram db list
```

Database commands require `lexigram-sql` to be installed:

```bash
uv add lexigram-sql
```

### Code Generation (`gen`)

```bash
# List all available generators
lexigram gen list

# Generate code
lexigram gen model User
lexigram gen service UserService
lexigram gen repository UserRepository
lexigram gen controller UserController
```

Generators are contributed by installed packages. Each generator creates files in the current project's source tree.

### Runtime Inspection (`inspect`)

```bash
# List registered container providers
lexigram inspect providers

# Show HTTP routes
lexigram inspect routes

# Display container bindings
lexigram inspect container

# Run health checks
lexigram inspect health

# View service list
lexigram inspect services
```

### Interactive Shell (`shell`)

```bash
# Start a REPL with the application context pre-loaded
lexigram shell

# Plain Python REPL without app bootstrap
lexigram shell --no-app

# Use IPython if available
lexigram shell --ipython
```

The shell provides `app`, `container`, `config`, `db`, `cache`, and `events` as pre-loaded objects.

### Other Commands

```bash
# System information
lexigram system info
lexigram version

# Configuration management
lexigram config show
lexigram config set default_template=full

# Contributor discovery
lexigram contrib check
lexigram contrib list

# Meta commands
lexigram list         # list all commands
lexigram completion   # generate shell completion
lexigram test         # run project tests
lexigram lint         # run project linters
```

---

## Integration with the DI Container

```python
from lexigram import Application
from lexigram.cli import CLIModule, CLIConfig
from lexigram.cli.di.provider import CLIProvider

# Via module (recommended)
app = Application(name="my-app")
app.add_module(CLIModule.configure(CLIConfig(default_template="full")))

# Via provider directly
provider = CLIProvider(config=CLIConfig(verbose=True))
app.add_provider(provider)
```

The `CLIProvider` has priority `APPLICATION` (40) — it boots after infrastructure but before domain services.

---

## Best Practices

- ✅ Run `lexigram gen list` to see all available generators from installed packages
- ✅ Use `lexigram project test/lint` as a pre-commit gate
- ✅ Run `lexigram contrib check` to verify contributors load cleanly after adding packages
- ✅ Use `--json` flag for machine-readable output (useful in CI scripts)
- ❌ Don't manually edit generated file headers — re-run the generator instead
- ❌ Don't use `lexigram run` in production — deploy through your ASGI server directly
