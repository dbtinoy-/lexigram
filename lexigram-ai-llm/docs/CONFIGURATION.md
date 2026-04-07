---
title: lexigram-ai-llm Configuration
description: Every config key for `ClientConfig` with types, defaults, and env-var names.
---

The config section key is `ai_llm`. Environment prefix: `LEX_AI_LLM__`.

## ClientConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AI_LLM__ENABLED` | Enable the LLM subsystem |
| `provider` | `ModelProvider` (str enum) | `"openai"` | `LEX_AI_LLM__PROVIDER` | LLM provider name |
| `model` | `str` | `"gpt-4-turbo"` | `LEX_AI_LLM__MODEL` | Model name or identifier |
| `api_key` | `SecretStr \| None` | `None` | `LEX_AI_LLM__API_KEY` | API key for the provider |
| `api_base` | `str \| None` | `None` | `LEX_AI_LLM__API_BASE` | Custom API base URL |
| `temperature` | `float` | `0.7` | `LEX_AI_LLM__TEMPERATURE` | Sampling temperature (0.0–2.0) |
| `max_tokens` | `int \| None` | `None` | `LEX_AI_LLM__MAX_TOKENS` | Max tokens in response |
| `timeout` | `float` | `60.0` | `LEX_AI_LLM__TIMEOUT` | Request timeout in seconds |
| `enable_cache` | `bool` | `False` | `LEX_AI_LLM__ENABLE_CACHE` | Enable response caching |
| `cache_ttl` | `int` | `3600` | `LEX_AI_LLM__CACHE_TTL` | Cache TTL in seconds |
| `thinking` | `ThinkingConfig \| None` | `None` | `LEX_AI_LLM__THINKING__*` | Thinking/reasoning config |
| `extra` | `dict[str, Any]` | `{}` | `LEX_AI_LLM__EXTRA__*` | Provider-specific extra params |

## ThinkingConfig sub-fields

When `thinking` is set, the `ThinkingConfig` object supports:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `suppress` | `bool` | `False` | Actively suppress thinking tokens |
| `budget_tokens` | `int` | `10000` | Max tokens for reasoning |
| `level` | `str \| None` | `None` | Gemini 3 thinking level (`minimal`, `low`, `medium`, `high`) |
| `effort` | `str \| None` | `None` | OpenAI reasoning effort (`low`, `medium`, `high`) |

## Example YAML

```yaml
# application.yaml
ai_llm:
  provider: openai
  model: gpt-4o
  temperature: 0.3
  max_tokens: 2000
  timeout: 30
  enable_cache: true
  cache_ttl: 7200
  thinking:
    budget_tokens: 5000
```

## Env-var overrides

```bash
export LEX_AI_LLM__PROVIDER=anthropic
export LEX_AI_LLM__MODEL=claude-sonnet-4-20250514
export LEX_AI_LLM__API_KEY=sk-ant-...
export LEX_AI_LLM__TEMPERATURE=0.0
export LEX_AI_LLM__ENABLE_CACHE=true
```

## Provider extras

Install the provider-specific client library:

```bash
uv add "lexigram-ai-llm[openai]"    # openai, tiktoken
uv add "lexigram-ai-llm[anthropic]" # anthropic
uv add "lexigram-ai-llm[ollama]"    # ollama
uv add "lexigram-ai-llm[groq]"     # groq
uv add "lexigram-ai-llm[cohere]"   # cohere
uv add "lexigram-ai-llm[mistral]"  # mistralai
```
