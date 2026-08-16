---
title: lexigram-workflow Configuration
description: Every config key for the workflow subsystem
---

Config section: `workflow` (config_key in `WorkflowProvider`, `config_model = BulkOperationConfig`).

The graph engine has a separate config (`GraphConfig`) registered as a singleton; its env vars use the prefix `LEX_WORKFLOW__GRAPH__`.

## `BulkOperationConfig`

Environment variable prefix: `LEX_WORKFLOW__` (e.g. `LEX_WORKFLOW__BATCH_SIZE=200`).

Defined in `lexigram.workflow.config.BulkOperationConfig`.

| Key | Type | Default | Env var | Description |
|---|---|---|---|---|
| `batch_size` | `int` | `10` | `LEX_WORKFLOW__BATCH_SIZE` | Items per batch |
| `max_concurrency` | `int` | `5` | `LEX_WORKFLOW__MAX_CONCURRENCY` | Max concurrent operations |
| `timeout` | `float` | `300.0` | `LEX_WORKFLOW__TIMEOUT` | Operation timeout in seconds |
| `retry_attempts` | `int` | `3` | `LEX_WORKFLOW__RETRY_ATTEMPTS` | Retry attempts on failure |
| `retry_delay` | `float` | `1.0` | `LEX_WORKFLOW__RETRY_DELAY` | Delay between retries (seconds) |
| `enable_progress_tracking` | `bool` | `True` | `LEX_WORKFLOW__ENABLE_PROGRESS_TRACKING` | Track operation progress |
| `circuit_breaker_config` | `CircuitBreakerConfig \| None` | `None` | — | Circuit breaker for bulk ops |
| `pipeline_timeout` | `float` | `60.0` | `LEX_WORKFLOW__PIPELINE_TIMEOUT` | Default pipeline timeout (seconds) |

## `GraphConfig`

Environment variable prefix: `LEX_WORKFLOW__GRAPH__` (e.g. `LEX_WORKFLOW__GRAPH__ENABLED=false`).

Defined in `lexigram.workflow.config.GraphConfig`.

| Key | Type | Default | Env var | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `True` | `LEX_WORKFLOW__GRAPH__ENABLED` | Enable graph subsystem |
| `max_iterations` | `int` | `25` | `LEX_WORKFLOW__GRAPH__MAX_ITERATIONS` | Max traversal steps (anti-loop) |
| `node_timeout` | `float` | `120.0` | `LEX_WORKFLOW__GRAPH__NODE_TIMEOUT` | Per-node timeout (0 = no limit) |
| `total_timeout` | `float` | `0.0` | `LEX_WORKFLOW__GRAPH__TOTAL_TIMEOUT` | Total workflow timeout (0 = no limit) |
| `checkpoint_enabled` | `bool` | `False` | `LEX_WORKFLOW__GRAPH__CHECKPOINT_ENABLED` | Persist checkpoints for resumption |
| `parallel_branches` | `bool` | `True` | `LEX_WORKFLOW__GRAPH__PARALLEL_BRANCHES` | Execute parallel branches via `asyncio.gather` |
| `max_parallel_branches` | `int` | `0` | `LEX_WORKFLOW__GRAPH__MAX_PARALLEL_BRANCHES` | Max parallel branches (0 = unlimited) |

## YAML example

```yaml
workflow:
  batch_size: 100
  max_concurrency: 10
  timeout: 600.0
  retry_attempts: 5
  retry_delay: 2.0
  enable_progress_tracking: true
  pipeline_timeout: 120.0
```

## Env-var override example

```bash
export LEX_WORKFLOW__BATCH_SIZE=200
export LEX_WORKFLOW__MAX_CONCURRENCY=20
export LEX_WORKFLOW__GRAPH__ENABLED=true
export LEX_WORKFLOW__GRAPH__CHECKPOINT_ENABLED=true
export LEX_WORKFLOW__GRAPH__MAX_ITERATIONS=50
```

The `WorkflowProvider` resolves `BulkOperationConfig` from the application config via `LexigramConfig.get_section("workflow", BulkOperationConfig)`. `GraphConfig` is instantiated separately and registered as a singleton.
