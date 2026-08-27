# LLM Router Demo

Teaches `lexigram-ai-llm` — multi-provider routing, streaming,
structured extraction, and the DI lifecycle with a test stand-in.

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — demo settings |
| 2 | `src/content_gen/app.py` | Composition root — module wiring |
| 3 | `src/content_gen/di/provider.py` | Provider lifecycle — register, boot, shutdown |
| 4 | `src/content_gen/services/` | Business logic — LLM usage patterns |
| 5 | `src/content_gen/repository/scripted_llm.py` | Test stand-in — ScriptedLLMClient |
| 6 | `tests/` | Deterministic testing without real LLM calls |

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
