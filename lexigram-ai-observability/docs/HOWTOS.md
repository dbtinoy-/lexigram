---
title: lexigram-ai-observability How-Tos
description: Task-oriented recipes for AI observability.
---

## Trace a Custom LLM Call

```python
from lexigram.ai.observability import AITracer
from lexigram.contracts.observability.tracing import TracerProtocol

# AITracer is injected by the container
tracer: AITracer  # resolved from container

with tracer.trace_llm_call("anthropic", "claude-3-opus") as span:
    response = await client.complete(messages)
    span.set_attribute("llm.tokens.total", response.usage.total_tokens)
```

## Record a Custom Metric

```python
from lexigram.ai.observability import AIMetrics

metrics: AIMetrics  # resolved from container

metrics.llm_requests_total.increment(
    labels={"provider": "openai", "model": "gpt-4o", "status": "success"}
)
metrics.llm_cost_dollars.increment(
    amount=0.0021,
    labels={"provider": "openai", "model": "gpt-4o"},
)
```

## Register a Health Check

```python
from lexigram.ai.observability import AIHealthMonitor
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

monitor: AIHealthMonitor  # resolved from container

async def check_openai() -> HealthCheckResult:
    try:
        # Ping the API
        await openai_client.models.list()
        return HealthCheckResult(
            component="llm.openai",
            status=HealthStatus.HEALTHY,
        )
    except Exception as e:
        return HealthCheckResult(
            component="llm.openai",
            status=HealthStatus.UNHEALTHY,
            error=str(e),
        )

monitor.add_llm_check("openai", check_openai)
results = await monitor.check_all()
```

## Use Tracing Decorators

```python
from lexigram.ai.observability import trace_llm, trace_vector

@trace_llm(provider="openai", model="gpt-4o", tracer=tracer)
async def complete_with_tracing(messages):
    return await llm_client.complete(messages)

@trace_vector(operation="search", provider="pgvector", tracer=tracer, collection="docs")
async def search_with_tracing(query, k=10):
    return await vector_store.search(query, top_k=k)
```

## Disable Observability for Local Dev

```python
from lexigram.ai.observability.config import ObservabilityConfig

config = ObservabilityConfig(
    enabled=False,  # completely disables the provider
)
module = ObservabilityModule.configure(config)
```

## How do I track embedding operations?

```python
from lexigram.ai.observability import track_embedding_operation, AITracer

# Decorator form — auto-instruments an embedding function
@track_embedding_operation(model="text-embedding-3-small", metrics=metrics)
async def embed_batch(texts: list[str]) -> list[list[float]]:
    return await embedding_client.embed(texts)

# Context manager form — fine-grained control with span attributes
tracer: AITracer  # resolved from container
with tracer.trace_embedding_operation("text-embedding-3-small", batch_size=10) as span:
    embeddings = await embedder.embed(texts)
    span.set_attribute("embedding.dimensions", len(embeddings[0]))
    span.set_attribute("embedding.batch_size", len(texts))
```

## How do I wrap AI clients manually without the container?

```python
from lexigram.ai.observability import ObservableLLMClient, ObservableVectorStore

# Wrap an existing LLM client with tracing and metrics
llm_client = ObservableLLMClient(
    delegate=raw_llm_client,
    provider="openai",
    model="gpt-4o",
    tracer=tracer,
    metrics=metrics,
)

# The wrapper exposes the same interface — no caller changes needed
response = await llm_client.complete(messages)

# Wrap a vector store the same way
vector_store = ObservableVectorStore(
    delegate=raw_vector_store,
    backend="pgvector",
    collection="documents",
    tracer=tracer,
    metrics=metrics,
)

results = await vector_store.search(query="find similar", k=5)
```

## How do I run comprehensive health checks for all AI dependencies?

```python
from lexigram.ai.observability import AIHealthMonitor
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

monitor: AIHealthMonitor  # resolved from container

# Register checks for all dependency types
monitor.add_llm_check("openai", check_openai)
monitor.add_vector_check("pgvector", check_pgvector)
monitor.add_cache_check("redis", check_redis)
monitor.add_embedding_check("text-embedding-3-small", check_embedding)

# Get all results
results = await monitor.check_all()

# Quick readiness probes
ready = await monitor.is_ready()  # True if every component is HEALTHY or DEGRADED
live = await monitor.is_live()    # True if at least one component is HEALTHY

# Check a single provider directly
openai_health = await monitor.check_llm("openai")
```

## Trace a RAG Pipeline Stage

```python
from lexigram.ai.observability import trace_rag

@trace_rag(stage="retrieval", tracer=tracer, pipeline="default")
async def retrieve_documents(query: str) -> list[Document]:
    return await retriever.retrieve(query)

@trace_rag(stage="synthesis", tracer=tracer, pipeline="default")
async def synthesize_answer(query: str, documents: list[Document]) -> str:
    return await llm.complete(format_prompt(query, documents))
```
