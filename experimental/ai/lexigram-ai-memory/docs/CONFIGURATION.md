---
title: lexigram-ai-memory Configuration
description: All configuration keys for MemoryConfig and its sub-configs.
---

## Config Section

The config section key is **`ai_memory`**.

```yaml
# application.yaml
ai_memory:
  enabled: true
  default_backend: in_memory
  ttl_seconds: 2592000
  working:
    system_prompt_tokens: 512
    recent_turns_fraction: 0.4
    episodic_fraction: 0.3
    semantic_fraction: 0.2
    tool_descriptions_fraction: 0.1
    max_recent_turns: 20
  episodic:
    default_top_k: 10
    recency_weight: 0.3
    importance_weight: 0.2
    relevance_weight: 0.5
    ttl_seconds: 0
  semantic:
    min_confidence: 0.5
    max_facts_per_entity: 100
  consolidation:
    enabled: true
    interval_seconds: 3600.0
    age_threshold_hours: 24.0
    importance_prune_threshold: 0.1
    batch_size: 100
```

## Root: `MemoryConfig`

| Name | Type | Default | Env Var | Description |
|------|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AI_MEMORY__ENABLED` | Enable the AI memory subsystem |
| `default_backend` | `str` | `"in_memory"` | `LEX_AI_MEMORY__DEFAULT_BACKEND` | Backend type (`in_memory`, `cache`, `database`, `vector`) |
| `ttl_seconds` | `int` | `2592000` | `LEX_AI_MEMORY__TTL_SECONDS` | Default entry TTL (0 = never expire) |

## Sub-config: `WorkingMemoryConfig`

| Name | Type | Default | Env Var | Description |
|------|------|---------|---------|-------------|
| `system_prompt_tokens` | `int` | `512` | `LEX_AI_MEMORY__WORKING__SYSTEM_PROMPT_TOKENS` | Fixed token allocation for system prompt |
| `recent_turns_fraction` | `float` | `0.4` | `LEX_AI_MEMORY__WORKING__RECENT_TURNS_FRACTION` | Fraction of remaining budget for recent turns |
| `episodic_fraction` | `float` | `0.3` | `LEX_AI_MEMORY__WORKING__EPISODIC_FRACTION` | Fraction for episodic recall |
| `semantic_fraction` | `float` | `0.2` | `LEX_AI_MEMORY__WORKING__SEMANTIC_FRACTION` | Fraction for semantic facts |
| `tool_descriptions_fraction` | `float` | `0.1` | `LEX_AI_MEMORY__WORKING__TOOL_DESCRIPTIONS_FRACTION` | Fraction for tool descriptions |
| `max_recent_turns` | `int` | `20` | `LEX_AI_MEMORY__WORKING__MAX_RECENT_TURNS` | Hard cap on recent turns |

## Sub-config: `EpisodicMemoryConfig`

| Name | Type | Default | Env Var | Description |
|------|------|---------|---------|-------------|
| `default_top_k` | `int` | `10` | `LEX_AI_MEMORY__EPISODIC__DEFAULT_TOP_K` | Default number of episodes to retrieve |
| `recency_weight` | `float` | `0.3` | `LEX_AI_MEMORY__EPISODIC__RECENCY_WEIGHT` | Weight for temporal recency |
| `importance_weight` | `float` | `0.2` | `LEX_AI_MEMORY__EPISODIC__IMPORTANCE_WEIGHT` | Weight for entry importance |
| `relevance_weight` | `float` | `0.5` | `LEX_AI_MEMORY__EPISODIC__RELEVANCE_WEIGHT` | Weight for semantic similarity |
| `ttl_seconds` | `int` | `0` | `LEX_AI_MEMORY__EPISODIC__TTL_SECONDS` | Entry TTL (0 = never expire) |

## Sub-config: `SemanticMemoryConfig`

| Name | Type | Default | Env Var | Description |
|------|------|---------|---------|-------------|
| `min_confidence` | `float` | `0.5` | `LEX_AI_MEMORY__SEMANTIC__MIN_CONFIDENCE` | Minimum confidence to store a fact |
| `max_facts_per_entity` | `int` | `100` | `LEX_AI_MEMORY__SEMANTIC__MAX_FACTS_PER_ENTITY` | Hard cap on facts per entity |

## Sub-config: `ConsolidationConfig`

| Name | Type | Default | Env Var | Description |
|------|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AI_MEMORY__CONSOLIDATION__ENABLED` | Enable automatic consolidation |
| `interval_seconds` | `float` | `3600.0` | `LEX_AI_MEMORY__CONSOLIDATION__INTERVAL_SECONDS` | How often to run a consolidation pass |
| `age_threshold_hours` | `float` | `24.0` | `LEX_AI_MEMORY__CONSOLIDATION__AGE_THRESHOLD_HOURS` | Min entry age before consolidation |
| `importance_prune_threshold` | `float` | `0.1` | `LEX_AI_MEMORY__CONSOLIDATION__IMPORTANCE_PRUNE_THRESHOLD` | Entries below this are prunable |
| `batch_size` | `int` | `100` | `LEX_AI_MEMORY__CONSOLIDATION__BATCH_SIZE` | Max entries per consolidation pass |

## Env Var Override

Prefix: `LEX_AI_MEMORY__`, nested delimiter `__`:

```bash
export LEX_AI_MEMORY__DEFAULT_BACKEND=cache
export LEX_AI_MEMORY__WORKING__MAX_RECENT_TURNS=50
export LEX_AI_MEMORY__CONSOLIDATION__INTERVAL_SECONDS=7200
```
