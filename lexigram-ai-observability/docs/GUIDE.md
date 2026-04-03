---
title: lexigram-ai-observability Guide
description: Tracing, metrics, and health monitoring for AI operations.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-llm` | Optional | LLM tracing |
| `lexigram-ai-rag` | Optional | RAG tracing |
| `lexigram-ai-agents` | Optional | Agent tracing |
| `lexigram-vector` | Optional | Vector store tracing |

## The Problem

LLM calls and vector searches are opaque — they cross process boundaries to external APIs and databases. When a response is slow, costs spike, or errors rise, you need visibility into what happened. Without instrumentation, debugging AI pipelines is guesswork.

`lexigram-ai-observability` solves this by wrapping your AI clients with distributed tracing, metrics collection, and health monitoring — automatically.

## Mental Model

The package has three pillars:

| Pillar | Class | What It Tracks |
|--------|-------|----------------|
| **Tracing** | `AITracer` | Per-call spans for LLM completions, vector operations, RAG stages, and embeddings |
| **Metrics** | `AIMetrics` | Counters, histograms, and gauges for tokens, costs, latency, request volume, and cache hit rates |
| **Health** | `AIHealthMonitor` | Registered health checks for LLM endpoints, vector stores, and embedding services |

These three work together via `ObservabilityProvider`, which auto-wires them around any `LLMClientProtocol` or `VectorStoreProtocol` registered in the container.

## Core Concepts

### Trace Spans

`AITracer` creates OpenTelemetry-compatible spans for every AI operation:

```python
from lexigram.ai.observability import AITracer

# Typical usage — spans are created automatically by ObservableLLMClient
with tracer.trace_llm_call("openai", "gpt-4o") as span:
    response = await client.complete(messages)
    span.set_attribute("llm.tokens.total", response.usage.total_tokens)
```

Available span helpers:

| Method | Creates Span Named |
|--------|-------------------|
| `trace_llm_call(provider, model)` | `llm.{provider}.{model}` |
| `trace_vector_operation(op, provider, collection)` | `vector.{op}.{provider}` |
| `trace_embedding_operation(model)` | `embedding.{model}` |
| `trace_rag_stage(stage, pipeline)` | `rag.{stage}` |
| `trace_rag_query(query)` | `rag.query` |

### Metrics

`AIMetrics` registers pre-defined instruments through `MetricsCollectorProtocol`. All metric names use the `intelligence_` prefix:

```python
from lexigram.ai.observability import AIMetrics

# Count a successful LLM call
metrics.llm_requests_total.increment(
    labels={"provider": "openai", "model": "gpt-4o", "status": "success"}
)
# Record latency
metrics.llm_duration_seconds.observe(value=0.8, labels={"provider": "openai", "model": "gpt-4o"})
```

### Auto-Wrapping

The killer feature: `ObservabilityProvider.boot()` detects existing `LLMClientProtocol` and `VectorStoreProtocol` registrations in the container and replaces them with `ObservableLLMClient` / `ObservableVectorStore` proxies. The proxy delegates every call to the original while recording spans and metrics.

```python
# After boot, this call is automatically traced and metered:
result = await llm_client.complete(messages)
# No code changes needed — the wrapping was transparent.
```

### Health Monitoring

`AIHealthMonitor` manages health checks for AI infrastructure:

```python
from lexigram.ai.observability import AIHealthMonitor

monitor = AIHealthMonitor()
monitor.add_llm_check("openai", check_openai_connectivity)
monitor.add_vector_check("pgvector", check_pgvector_connectivity)

all_healthy = await monitor.is_ready()
```

## Typical Usage

### Full Application Wiring

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.observability import ObservabilityModule
from lexigram.ai.llm import LLMModule
from lexigram.ai.observability.config import ObservabilityConfig

config = LexigramConfig.from_yaml({
    "ai_observability": {
        "enabled": True,
        "tracing_enabled": True,
        "metrics_enabled": True,
        "health_checks_enabled": True,
    }
})

app = Application(name="observable-app", config=config)
app.add_module(LLMModule.configure())
app.add_module(ObservabilityModule.configure())
await app.start()
# Your AI calls are now instrumented
```

### Using the Decorators

For custom functions that aren't auto-wrapped, use the decorator API:

```python
from lexigram.ai.observability import trace_llm, track_llm_call

@trace_llm(provider="openai", model="gpt-4o", tracer=tracer)
@track_llm_call(provider="openai", model="gpt-4o", metrics=metrics)
async def my_completion(messages):
    return await client.complete(messages)
```

## Common Patterns

### Selective Disabling

```python
config = ObservabilityConfig(
    enabled=True,
    metrics_enabled=False,   # disable metrics, keep tracing
    tracing_enabled=True,
)
```

### Custom Metric Labels

Labels flow through `AIMetrics` to `MetricsCollectorProtocol` — add them everywhere for granular breakdowns:

```python
metrics.llm_requests_total.increment(labels={
    "provider": "openai",
    "model": "gpt-4o",
    "status": "success",
    "deployment": "prod-eu-west-1",
})
```

### Hook Integration

The package emits lifecycle hooks you can subscribe to:

```python
from lexigram.ai.observability.hooks import LLMCallTracedHook
# Hook payload fired after each traced LLM call
```

## Best Practices

- Enable tracing and metrics in production — the overhead is minimal (`MetricsCollectorProtocol` is designed for hot paths).
- Register health checks for every external AI dependency (LLM provider, vector store).
- Use `tracing_enabled=false` during local development if you don't need spans.
- Attach meaningful span attributes (`tokens.total`, `cost`, `error.type`) via the wrapper or decorator callbacks.

## Next Steps

- [How-Tos](./HOWTOS.md) — practical recipes
- [Architecture](./ARCHITECTURE.md) — internal design
- [Configuration](./CONFIGURATION.md) — every config key
