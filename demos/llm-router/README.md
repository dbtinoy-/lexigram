# LLM Router Demo

Teaches the **Lexigram LLM client pattern** — ScriptedLLMClient for deterministic
testing, content generation, and structured product extraction.  Demonstrates
how to build LLM-powered services without making real API calls.

## What you'll learn

1. **ScriptedLLMClient** — deterministic test stand-in that returns pre-defined responses
2. **Content generation** — prompt engineering with style control and retries
3. **Structured extraction** — parsing LLM responses into typed data
4. **Provider wiring** — injecting LLM clients via DI

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — writing style, retries, LLM settings |
| 2 | `src/content_gen/app.py` | Composition root — `build_modules()` + `build_providers()` |
| 3 | `src/content_gen/di/provider.py` | Provider lifecycle — `register()`, `boot()`, `health_check()` |
| 4 | `src/content_gen/config.py` | Config model — `BaseConfig` + `Field()` with descriptions |
| 5 | `src/content_gen/repository/scripted_llm.py` | Test stand-in — deterministic LLM responses |
| 6 | `src/content_gen/services/generator.py` | Content generation — prompt engineering with retries |
| 7 | `src/content_gen/services/extractor.py` | Structured extraction — parsing JSON from LLM |
| 8 | `src/content_gen/controllers/api.py` | HTTP surface — thin controller adapters |
| 9 | `tests/` | Real composition root, no mocks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      application.yaml                           │
│  web: server/host/port, security/csrf/enabled                  │
│  content_gen: default_style, max_retries                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│  build_modules()  → [WebModule.configure(controllers=[...])]    │
│  build_providers() → [ContentGenProvider()]                     │
│  create_app()     → Application(name="llm-router")             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      provider.py                                │
│  register(): container.singleton(ContentGenConfig, instance=cfg)│
│  boot():     resolve config → create LLM client → bind controller│
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                repository/scripted_llm.py                        │
│  ScriptedLLMClient — deterministic responses for testing        │
│  Returns pre-defined responses based on prompt keywords         │
└─────────────────────────────────────────────────────────────────┘
```

## Quick start

```bash
cd demos/llm-router
uv run python -m content_gen
```

## Run tests

```bash
cd demos/llm-router
uv run pytest tests/ -v
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/content/generate` | Generate content with a given style |
| `POST` | `/api/content/extract` | Extract product info from description |
| `GET` | `/api/content/health` | Health check |

## Switching to a real LLM

Replace `ScriptedLLMClient` in `provider.py` with a real client:

```python
from lexigram.ai.llm import OllamaClient, ClientConfig

llm_client = OllamaClient(config=ClientConfig(model="llama3"))
```
