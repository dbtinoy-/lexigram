---
title: lexigram-ai Configuration
description: Every config key for the AI subsystem, with types, defaults, and env-var names.
---

The config section key is `ai` (configures `AIConfig`). Environment prefix: `LEX_AI__`.

## AIConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `name` | `str` | `"ai"` | `LEX_AI__NAME` | Configuration name |
| `enabled` | `bool` | `True` | `LEX_AI__ENABLED` | Enable AI features |
| `llm` | `ClientConfig \| None` | `None` | `LEX_AI_LLM__*` | LLM client configuration |
| `vector` | `VectorConfig \| None` | `None` | `LEX_VECTOR__*` | Vector store configuration |
| `rag` | `RAGConfig \| None` | `None` | `LEX_AI_RAG__*` | RAG pipeline configuration |
| `governance` | `GovernanceConfig` | default-factory (disabled when governance package absent) | `LEX_AI_GOVERNANCE__*` | AI governance configuration |
| `observability` | `ObservabilityConfig` | default-factory (disabled if `lexigram-ai-observability` not installed) | `LEX_AI_OBSERVABILITY__*` | AI observability configuration |
| `subsystems` | `dict[str, dict[str, Any]]` | `{}` | `LEX_AI__SUBSYSTEMS__*` | Dynamic config for third-party subsystems |

## Example YAML

```yaml
# application.yaml
ai:
  enabled: true
  llm:
    provider: openai
    model: gpt-4o
    api_key: ${LEX_AI_LLM__API_KEY}
    temperature: 0.7
    timeout: 60
  governance:
    enabled: true
  subsystems:
    custom_subsystem:
      option_a: value
```

## Env-var overrides

The nested delimiter is `__` (double underscore):

```bash
export LEX_AI__ENABLED=true
export LEX_AI_LLM__PROVIDER=anthropic
export LEX_AI_LLM__MODEL=claude-sonnet-4-20250514
export LEX_AI_LLM__API_KEY=sk-ant-...
export LEX_AI_LLM__TEMPERATURE=0.3
```

## Subsystem configuration

Use `get_subsystem_config()` to retrieve config for a dynamically-discovered subsystem:

```python
from lexigram.ai.config import AIConfig, get_subsystem_config

config = AIConfig()
sub_cfg = get_subsystem_config(config, "llm")
# Returns config.llm if set, otherwise config.subsystems["llm"]
```

## Production security

`AIConfig` includes a `model_validator` that blocks insecure API keys (`sk-...`, `sk-test`, `change-me`) when `LEX_ENV=production`.
