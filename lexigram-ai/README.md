# lexigram-ai

AI Layer for Lexigram Framework - Native LLM, Vector, RAG integration

---

## Overview

`lexigram-ai` is the **AI orchestration layer** for the Lexigram Framework. It is a thin coordinator package that wires together independent AI sub-packages (`lexigram-ai-llm`, `lexigram-ai-rag`, `lexigram-ai-agents`, etc.) via the framework's DI container and entry-point discovery, and exposes a single `AIModule` entry point for application composition. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai
# Optional extras
uv add "lexigram-ai[llm,vector,rag,governance,observability]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai import AIModule

@module(imports=[AIModule.configure()])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

## Configuration

> **Zero-config usage:** Call `AIModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai:
  llm:
    default_provider: "openai"
    openai:
      api_key: "${OPENAI_API_KEY}"
  rag:
    enabled: true
  governance:
    enabled: true
    monthly_budget: 1000.0
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_PROFILE=production
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.config import AIConfig
from lexigram.ai import AIModule

config = AIConfig(...)
AIModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI__ENABLED` | Global AI feature toggle |
| `llm` | `None` | `LEX_AI_LLM__*` | LLM provider config |
| `vector` | `None` | `LEX_AI__VECTOR__*` | Vector store config |
| `rag` | `None` | `LEX_AI__RAG__*` | RAG pipeline config |
| `governance` | default | `LEX_AI__GOVERNANCE__*` | Policy enforcement config |
| `observability` | default | `LEX_AI__OBSERVABILITY__*` | Tracing and metrics config |
| `subsystems` | `{}` | — | Config for third-party entry-point subsystems |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AIModule.configure(config)` | Configure with explicit config |
| `AIModule.stub()` | Minimal config for testing |

## Key Features

- **AI orchestration**: Thin coordinator wiring all AI sub-packages via DI
- **Entry-point discovery**: Discovers sub-packages via `lexigram.ai.subsystems` entry points
- **Multi-provider support**: Integrates LLM, RAG, agents, memory, governance, and observability
- **Production security**: Validates API keys in production environments

## Testing

```python
async with Application.boot(modules=[AIModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/__init__.py` | Lazy-loaded public API: `AIModule`, `AIProvider`, `AIConfig` |
| `src/lexigram/ai/module.py` | `AIModule.configure()` and `AIModule.stub()` |
| `src/lexigram/ai/config.py` | `AIConfig` and `get_subsystem_config()` |
| `src/lexigram/ai/di/provider.py` | `AIProvider` — registers and boots sub-providers |
| `src/lexigram/ai/exceptions.py` | `AIError` base exception |
