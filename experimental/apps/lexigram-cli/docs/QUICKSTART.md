---
title: lexigram-cli Quickstart
description: Install the Lexigram CLI and scaffold your first project in minutes
---

:::tip[Alpha]
Lexigram is **alpha (0.1.x)**. Pin versions in production and expect public APIs to evolve before 1.0.
:::

## Install

```bash
uv add lexigram-cli
```

Or install as a standalone tool:

```bash
uv tool install lexigram-cli
```

## Hello World

```bash
# Verify the CLI is available
lexigram --help

# Scaffold a new project
lexigram new project my-app --template web-api
cd my-app

# Start the dev server
lexigram dev --reload
```

## Primary Import + Provider Wiring

The CLI can be integrated into a DI container via `CLIModule`:

```python
from lexigram import Application
from lexigram.cli import CLIModule

app = Application(name="my-app")
app.add_module(CLIModule.configure())
```

Or using `CLIProvider` directly:

```python
from lexigram.cli import CLIConfig
from lexigram.cli.di.provider import CLIProvider

provider = CLIProvider(config=CLIConfig())
app.add_provider(provider)
```

## What Just Happened

- `lexigram new project` scaffolded a complete project structure with `pyproject.toml`, `src/`, `tests/`, and `application.yaml`
- `lexigram dev` auto-detected the `create_app()` factory and launched an ASGI dev server with hot-reload
- `CLIModule.configure()` registers the CLI provider and exports `CLIApplicationProtocol`

## Next Steps

- [Guide](./GUIDE.md) — full walkthrough of every CLI command
- [How-Tos](./HOWTOS.md) — task-oriented recipes
