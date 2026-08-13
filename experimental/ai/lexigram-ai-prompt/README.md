# lexigram-ai-prompt

AI prompt management for the Lexigram Framework — templates, composition, optimization

---

## Overview

Type-safe prompt template management for the Lexigram AI framework. Build, version, compose, and auto-optimize prompts via DI — with injection protection, multi-format rendering, and a DSPy-inspired optimizer built in. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai-prompt
# Optional extras
uv add "lexigram-ai-prompt[jinja2]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.prompt import PromptModule
from lexigram.ai.prompt.config import PromptConfig


@module(
    imports=[
        PromptModule.configure(
            PromptConfig(default_format="f_string", sanitize_inputs=True)
        )
    ]
)
class AppModule(Module):
    pass


async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `PromptModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_prompt:
  enabled: true
  default_format: "f_string"
  sanitize_inputs: true
  strict_sanitizer: true
  max_variable_length: 0
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_PROMPT__DEFAULT_FORMAT=jinja2
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.prompt.config import PromptConfig
from lexigram.ai.prompt import PromptModule

config = PromptConfig(
    default_format="jinja2",
    sanitize_inputs=True,
    strict_sanitizer=True,
    max_variable_length=4096,
)
PromptModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI_PROMPT__ENABLED` | Enable the AI prompt subsystem |
| `default_format` | `"f_string"` | `LEX_AI_PROMPT__DEFAULT_FORMAT` | Rendering format when templates don't specify one |
| `sanitize_inputs` | `True` | `LEX_AI_PROMPT__SANITIZE_INPUTS` | Scan variable values for injection patterns |
| `strict_sanitizer` | `True` | `LEX_AI_PROMPT__STRICT_SANITIZER` | Raise on detected injection |
| `max_variable_length` | `0` | `LEX_AI_PROMPT__MAX_VARIABLE_LENGTH` | Max variable value length in chars |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `PromptModule.configure(config)` | Configure with explicit config |
| `PromptModule.stub()` | Minimal config for testing |

## Key Features

- **Template types**: `StringPromptTemplate`, `ChatPromptTemplate`, `FewShotPromptTemplate`, `PartialPromptTemplate`
- **Rendering formats**: f_string, jinja2, dollar, and simple templates
- **Registry**: Named prompt lookup via `PromptRegistry`
- **Versioning**: `VersionedPromptStore` with history and rollback
- **Composition**: `PromptPipeline` (sequential) and `ConditionalPrompt` (branching)
- **Optimizer**: DSPy-inspired automatic prompt improvement with BOOTSTRAP_FEW_SHOT, TEMPLATE_REFINEMENT, and ENSEMBLE strategies

## Testing

```python
async with Application.boot(modules=[PromptModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/prompt/module.py` | `PromptModule.configure()`, `.stub()` |
| `src/lexigram/ai/prompt/config.py` | `PromptConfig` |
| `src/lexigram/ai/prompt/template/string.py` | `StringPromptTemplate` |
| `src/lexigram/ai/prompt/template/chat.py` | `ChatPromptTemplate` |
| `src/lexigram/ai/prompt/template/few_shot.py` | `FewShotPromptTemplate` |
| `src/lexigram/ai/prompt/rendering/engine.py` | `PromptRenderer`, `RenderFormat` |
| `src/lexigram/ai/prompt/registry/registry.py` | `PromptRegistry` |
| `src/lexigram/ai/prompt/registry/versioned.py` | `VersionedPromptStore` |
| `src/lexigram/ai/prompt/composition/pipeline.py` | `PromptPipeline` |
| `src/lexigram/ai/prompt/optimization/optimizer.py` | `PromptOptimizer` |
| `src/lexigram/ai/prompt/di/provider.py` | `PromptProvider` |
