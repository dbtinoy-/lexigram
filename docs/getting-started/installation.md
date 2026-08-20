---
title: Installation
description: Install the Lexigram framework and get your environment ready
sidebar:
  order: 1
---

:::note[What you'll learn]
- Install Lexigram using **uv** (recommended) or pip
- Choose the right packages for your project
- Verify your installation
:::

:::tip[Alpha]
Lexigram is **alpha (0.1.x)**. Pin versions in production and expect public APIs to evolve before 1.0.
:::

## Requirements

- **Python 3.11** or higher
- **uv** (recommended) or pip

---

## Quick Install

```bash
# uv (recommended — fast, deterministic)
uv add lexigram

# pip
pip install lexigram
```

The core `lexigram` package gives you:

| Feature | Import | Description |
|---------|--------|-------------|
| `Application` | `from lexigram import Application` | Composition root with lifecycle management |
| `Provider` | `from lexigram import Provider` | Two-phase `register` / `boot` service wiring |
| `Container` | `from lexigram import Container` | IoC container — `singleton`, `scoped`, `transient` bindings |
| DI decorators | `from lexigram import singleton, injectable, scoped, transient` | Mark classes for auto-registration |
| `LexigramConfig` | `from lexigram import LexigramConfig` | YAML + env vars + profile overlays |
| `Result` | `from lexigram.result import Result, Ok, Err` | Explicit error handling with `unwrap`, `map`, `and_then` |
| `module` | `from lexigram import module, Module` | `@module` decorator with import/export boundaries |

`lexigram-contracts` (the zero-dependency protocol layer, imported as `lexigram.contracts.*`) is installed automatically as a dependency of `lexigram`.

---

## Common Stacks

Install only what you need. Every extension depends only on `lexigram` (core) and `lexigram-contracts` — never on each other.

### Web API

```bash
uv add lexigram-web
```

ASGI web layer — controllers, routing, middleware, OpenAPI docs, CORS, CSRF, rate limiting.

### Database

```bash
uv add lexigram-sql
```

Async SQL for Postgres / MySQL / SQLite — repositories, migrations, query building.

### AI

```bash
uv add lexigram-ai lexigram-ai-llm
```

Multi-provider LLM client and the orchestration layer. Add `lexigram-ai-rag`, `lexigram-ai-agents`, and `lexigram-vector` as needed.

---

## All Packages

The open-source ecosystem is 35+ extensions across these areas. See **[The Ecosystem](/ecosystem/)** for the full, annotated list.

| Category | Packages |
|----------|----------|
| **Foundation** | `lexigram`, `lexigram-contracts` |
| **Web & API** | `lexigram-web`, `lexigram-http`, `lexigram-graphql` |
| **Data & Persistence** | `lexigram-sql`, `lexigram-nosql`, `lexigram-cache`, `lexigram-storage`, `lexigram-search`, `lexigram-vector`, `lexigram-graph` |
| **AI** | `lexigram-ai`, `lexigram-ai-llm`, `lexigram-ai-rag`, `lexigram-ai-agents`, `lexigram-ai-memory`, `lexigram-ai-skills`, `lexigram-ai-session`, `lexigram-ai-mcp`, `lexigram-ai-workers`, `lexigram-ai-feedback` |
| **Messaging & Workflow** | `lexigram-events`, `lexigram-queue`, `lexigram-notification`, `lexigram-webhook`, `lexigram-workflow` |
| **Background Work** | `lexigram-tasks` |
| **Observability & Reliability** | `lexigram-monitor`, `lexigram-resilience`, `lexigram-audit`, `lexigram-ai-observability` |
| **Security & Multi-Tenancy** | `lexigram-auth`, `lexigram-tenancy`, `lexigram-features` |
| **Developer Tooling** | `lexigram-cli`, `lexigram-testing` |

---

## Developer Tools

```bash
# CLI — project scaffolding, dev server, migrations
uv add lexigram-cli

# Testing — fakes, test clients, compliance suites
uv add --dev lexigram-testing
```

With `lexigram-cli` installed you get the `lexigram` command:

```bash
lexigram new project my-app   # scaffold a project (or: lexigram new package <name>)
lexigram run                  # auto-detect create_app() and serve
lexigram db upgrade           # run migrations
```

---

## Verify Installation

```bash
python -c "import lexigram; print(lexigram.__version__)"
```

---

## Next Steps

- [Your First App](/getting-started/first-app/) — Build a working API
- [Project Structure](/getting-started/project-structure/) — Recommended layouts
- [Core Concepts](/getting-started/core-concepts/) — Providers, DI, Result type, and modules
- [The Ecosystem](/ecosystem/) — Every package, grouped by purpose
