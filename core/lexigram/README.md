# lexigram

Async-first DI/IoC framework for Python — core package.

![Lexigram demo](docs/gifs/hero/lexigram-hero.gif)

---

## Overview

Lexigram is the foundation package for the wider Lexigram ecosystem. It provides the
DI/IoC container, application lifecycle, configuration system, provider protocol,
exception hierarchy, and structured logging foundation.

Async-first by design: application boot, provider lifecycle, I/O paths, and
resolution workflows are built for async Python. Use `Application.boot(...)` to
assemble modules and providers into a running app.

## Install

```bash
uv add lexigram
# Optional extras
uv add "lexigram[security]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.app.standard import StandardModule


@module(imports=[StandardModule.configure()])
class AppModule(Module):
    pass


async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `StandardModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
app_name: my-app
debug: false
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_PROFILE=production
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.config.main import LexigramConfig

config = LexigramConfig(...)
StandardModule.configure(config_class=LexigramConfig)
```

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `StandardModule.configure(...)` | Configure with explicit config, sources, or overrides |
| `StandardModule.build_providers()` | Provider list for `Application.boot(providers=[...])` |
| `CoreModule.configure(...)` | Stripped-down kernel without serialization or concurrency |

## Key Features

- **DI Container** — register services as singleton, transient, or scoped; resolve via `await container.resolve(ServiceType)`
- **Provider Lifecycle** — `register()`, `boot()`, `shutdown()` hooks with priority ordering
- **Result Pattern** — `Result[T, E]` for expected domain failures, exceptions for infrastructure errors
- **Module System** — compose applications from reusable modules with explicit exports
- **Structured Logging** — structlog-based logging via `get_logger(__name__)`
- **Configuration** — Pydantic-based config with YAML, environment variables, and profile support

## Testing

```python
async with Application.boot(modules=[StandardModule.configure()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/app/base.py` | Application lifecycle and boot flow |
| `src/lexigram/app/standard.py` | StandardModule.configure() with all kernel providers |
| `src/lexigram/di/container/container.py` | Container registration, scope, and diagnostics |
| `src/lexigram/result/` | Result, Ok, Err, and helpers |
| `src/lexigram/config/main.py` | LexigramConfig and configuration system |
