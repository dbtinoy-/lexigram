# lexigram-ai-agents

Agent system for Lexigram Framework - AI agents with tools, strategies, and execution

---

## Overview

Agent orchestration package for the Lexigram Framework. Provides agent base classes, tool registration, execution strategies (ReAct, Plan-and-Execute, Reflexion, Supervisor), observability, and multi-agent coordination — all wired through DI via `AgentsModule`. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai-agents
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.agents import AgentsModule
from lexigram.ai.agents.config import AgentConfig

@module(imports=[
    AgentsModule.configure(AgentConfig(max_iterations=10))
])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

## Configuration

> **Zero-config usage:** Call `AgentsModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_agents:
  max_iterations: 10
  default_temperature: 0.7
  default_max_tokens: 2048
  enable_tracing: true
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_AGENTS__MAX_ITERATIONS=15
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.agents.config import AgentConfig
from lexigram.ai.agents import AgentsModule

config = AgentConfig(max_iterations=10)
AgentsModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI_AGENTS__ENABLED` | Enable the agent subsystem |
| `max_iterations` | `10` | `LEX_AI_AGENTS__MAX_ITERATIONS` | Maximum reasoning iterations per execution |
| `default_temperature` | `0.7` | `LEX_AI_AGENTS__DEFAULT_TEMPERATURE` | Default LLM temperature |
| `default_max_tokens` | `2048` | `LEX_AI_AGENTS__DEFAULT_MAX_TOKENS` | Default max tokens for LLM responses |
| `tool_max_retries` | `3` | `LEX_AI_AGENTS__TOOL_MAX_RETRIES` | Retry attempts for transient tool errors |
| `enable_tracing` | `True` | `LEX_AI_AGENTS__ENABLE_TRACING` | Enable OpenTelemetry tracing |
| `enable_metrics` | `True` | `LEX_AI_AGENTS__ENABLE_METRICS` | Enable Prometheus metrics |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AgentsModule.configure(config, enable_multi_agent)` | Configure with explicit config |
| `AgentsModule.stub()` | Minimal config for testing |

## Key Features

- **Agent base classes**: `AgentBase` for defining agents with tools and system prompts
- **Execution strategies**: ReAct, Plan-and-Execute, Reflexion, Supervisor
- **Tool system**: `@tool` decorator for registering standalone tool functions
- **Multi-agent coordination**: `AgentAsToolAdapter` for agent-to-agent delegation
- **Observability**: Built-in tracing and metrics via `AgentTracer` and `AgentMetrics`

## Testing

```python
async with Application.boot(modules=[AgentsModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/agents/module.py` | `AgentsModule.configure()` and `stub()` |
| `src/lexigram/ai/agents/config.py` | `AgentConfig` and environment variable bindings |
| `src/lexigram/ai/agents/agent/base.py` | `AgentBase` class with tools and prompts |
| `src/lexigram/ai/agents/executor/executor.py` | `AgentExecutorImpl` — strategy execution loop |
| `src/lexigram/ai/agents/tools/registry.py` | `ToolRegistryImpl` and `@tool` decorator |
| `src/lexigram/ai/agents/strategies/react.py` | ReAct reasoning loop |
| `src/lexigram/ai/agents/di/provider.py` | `AgentsProvider` — registers agents into DI |
