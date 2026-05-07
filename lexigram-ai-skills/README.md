# lexigram-ai-skills

AI skills and tools for the Lexigram Framework — registry, executor, builtin tools, discovery

---

## Overview

Composable, registry-based skill execution for the Lexigram AI framework. Define skills as classes or decorated functions, execute them with retry, caching, permission enforcement, and timeout — and compose them into chains, pipelines, parallel fans, and content-routers. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai-skills
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.skills import SkillsModule
from lexigram.ai.skills.config import SkillsConfig

@module(imports=[
    SkillsModule.configure(
        SkillsConfig(
            enable_builtin=True,
            builtin_skills=["current_datetime", "math_calculate"],
            cache_enabled=True,
            enforce_permissions=False,
        )
    )
])
class AppModule(Module):
    pass

async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `SkillsModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_skills:
  default_timeout_seconds: 30.0
  cache_enabled: true
  enforce_permissions: true
  enable_builtin: true
  builtin_skills:
    - "current_datetime"
    - "math_calculate"
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_SKILLS__ENFORCE_PERMISSIONS=true
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.skills.config import SkillsConfig
from lexigram.ai.skills import SkillsModule

config = SkillsConfig(
    default_timeout_seconds=30.0,
    cache_enabled=True,
    enforce_permissions=True,
    enable_builtin=True,
    builtin_skills=["current_datetime", "math_calculate", "text_summarize"],
)
SkillsModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `default_timeout_seconds` | `30.0` | `LEX_AI_SKILLS__DEFAULT_TIMEOUT_SECONDS` | Execution timeout per skill |
| `max_retries` | `2` | `LEX_AI_SKILLS__MAX_RETRIES` | Retry attempts on failure |
| `max_concurrent_executions` | `10` | `LEX_AI_SKILLS__MAX_CONCURRENT_EXECUTIONS` | Semaphore cap on concurrent executions |
| `cache_enabled` | `True` | `LEX_AI_SKILLS__CACHE_ENABLED` | Global result caching switch |
| `cache_ttl_seconds` | `3600` | `LEX_AI_SKILLS__CACHE_TTL_SECONDS` | Default TTL for cached results |
| `enforce_permissions` | `True` | `LEX_AI_SKILLS__ENFORCE_PERMISSIONS` | Enable permission checks |
| `auto_discover` | `False` | `LEX_AI_SKILLS__AUTO_DISCOVER` | Scan `scan_packages` on boot |
| `enable_builtin` | `True` | `LEX_AI_SKILLS__ENABLE_BUILTIN` | Register built-in skills on boot |
| `builtin_skills` | (list) | `LEX_AI_SKILLS__BUILTIN_SKILLS` | Which built-in skills to register |
| `enable_skill_sources` | `True` | `LEX_AI_SKILLS__ENABLE_SKILL_SOURCES` | Scan external SKILL.md sources on boot |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `SkillsModule.configure(config)` | Configure with explicit config |
| `SkillsModule.stub(config)` | Minimal config for testing |

## Key Features

- **Class-based skills**: `AbstractSkill` base class with `SkillDefinition`
- **Function-based skills**: `@skill` decorator for registering functions
- **Skill executor**: Retry, caching, permissions, and timeout enforcement
- **Built-in skills**: DateTime, Math, HTTPRequest, WebSearch, FileRead, FileWrite, DatabaseQuery, CodeExecute
- **Composition**: `SkillChain`, `ParallelSkills`, `SkillPipeline`, `SkillRouter`
- **MCP bridge**: `MCPSkillBridge` imports MCP tools as skills and exports skills as MCP tools
- **Registry**: Named lookup and registration via `SkillRegistry`

## Testing

```python
async with Application.boot(modules=[SkillsModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/skills/module.py` | `SkillsModule.configure()`, `.stub()` |
| `src/lexigram/ai/skills/config.py` | `SkillsConfig` |
| `src/lexigram/ai/skills/base/core.py` | `AbstractSkill`, `FunctionSkill` |
| `src/lexigram/ai/skills/decorators/core.py` | `@skill`, `@skill_param` |
| `src/lexigram/ai/skills/executor/core.py` | `SkillExecutor` |
| `src/lexigram/ai/skills/registry/core.py` | `SkillRegistry` |
| `src/lexigram/ai/skills/composition/` | chain, parallel, pipeline, router |
| `src/lexigram/ai/skills/discovery/mcp_bridge.py` | `MCPSkillBridge` |
| `src/lexigram/ai/skills/di/provider.py` | `SkillsProvider` |
