---
title: lexigram-ai-agents Configuration
description: All configuration keys for AgentConfig.
---

## Config Section

The config section key is **`ai_agents`**.

```yaml
# application.yaml
ai_agents:
  enabled: true
  max_iterations: 10
  default_temperature: 0.7
  default_max_tokens: 2048
  tool_max_retries: 3
  enable_tracing: true
  enable_metrics: true
```

## All Keys

| Name | Type | Default | Env Var | Description |
|------|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AI_AGENTS__ENABLED` | Enable the AI agents subsystem |
| `max_iterations` | `int` | `10` | `LEX_AI_AGENTS__MAX_ITERATIONS` | Maximum reasoning iterations per execution |
| `default_temperature` | `float` | `0.7` | `LEX_AI_AGENTS__DEFAULT_TEMPERATURE` | Default temperature for LLM calls |
| `default_max_tokens` | `int` | `2048` | `LEX_AI_AGENTS__DEFAULT_MAX_TOKENS` | Default max tokens for LLM responses |
| `tool_max_retries` | `int` | `3` | `LEX_AI_AGENTS__TOOL_MAX_RETRIES` | Number of retries for transient tool execution errors |
| `enable_tracing` | `bool` | `True` | `LEX_AI_AGENTS__ENABLE_TRACING` | Enable OpenTelemetry tracing |
| `enable_metrics` | `bool` | `True` | `LEX_AI_AGENTS__ENABLE_METRICS` | Enable Prometheus metrics |

## Env Var Override

Environment variables use prefix `LEX_AI_AGENTS__`:

```bash
export LEX_AI_AGENTS__MAX_ITERATIONS=25
export LEX_AI_AGENTS__DEFAULT_TEMPERATURE=0.5
export LEX_AI_AGENTS__TOOL_MAX_RETRIES=5
```

## Disabling

Set `enabled: false` to skip agent service registration entirely. The provider exits early during `register()`.

## Limits

- `max_iterations`: min 1
- `default_temperature`: 0.0–2.0
- `tool_max_retries`: min 1
- `default_max_tokens`: min 1
