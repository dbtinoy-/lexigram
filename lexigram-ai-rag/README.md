# lexigram-ai-rag

Retrieval-Augmented Generation (RAG) pipeline for the Lexigram Framework

---

## Overview

RAG (Retrieval-Augmented Generation) pipeline for the Lexigram Framework. Provides a multi-stage, fully configurable pipeline covering ingestion, query processing, retrieval, context optimisation, synthesis, quality assurance, and post-processing — all wired through the DI container via `RAGModule`. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai-rag
# Optional extras
uv add "lexigram-ai-rag[pdf,web]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.rag import RAGModule
from lexigram.ai.rag.config import RAGConfig

@module(imports=[
    RAGModule.configure(
        RAGConfig(
            vector_store_type="pgvector",
            collection_name="my_docs",
            top_k=5,
            enable_citations=True,
        )
    )
])
class AppModule(Module):
    pass

async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `RAGModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_rag:
  vector_store_type: "pgvector"
  collection_name: "my_docs"
  top_k: 5
  embedding_model: "text-embedding-ada-002"
  enable_citations: true
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_RAG__VECTOR_STORE_TYPE=pgvector
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.rag.config import RAGConfig
from lexigram.ai.rag import RAGModule

config = RAGConfig(
    vector_store_type="pgvector",
    collection_name="my_docs",
    top_k=5,
)
RAGModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `vector_store_type` | `pgvector` | `LEX_AI_RAG__VECTOR_STORE_TYPE` | Backend: `pgvector`, `chroma`, `qdrant`, `mock` |
| `collection_name` | `default` | `LEX_AI_RAG__COLLECTION_NAME` | Collection / index name |
| `vector_dimension` | `1536` | `LEX_AI_RAG__VECTOR_DIMENSION` | Embedding dimension |
| `top_k` | `5` | `LEX_AI_RAG__TOP_K` | Documents to retrieve per query |
| `similarity_threshold` | `0.7` | `LEX_AI_RAG__SIMILARITY_THRESHOLD` | Minimum similarity score to include |
| `use_hybrid_search` | `True` | `LEX_AI_RAG__USE_HYBRID_SEARCH` | Combine semantic + keyword search |
| `embedding_provider` | `openai` | `LEX_AI_RAG__EMBEDDING_PROVIDER` | Embedding provider |
| `embedding_model` | `None` | `LEX_AI_RAG__EMBEDDING_MODEL` | Embedding model |
| `chunking_strategy` | `recursive` | `LEX_AI_RAG__CHUNKING_STRATEGY` | `recursive`, `semantic`, or `token` |
| `chunk_size` | `512` | `LEX_AI_RAG__CHUNK_SIZE` | Tokens per chunk |
| `chunk_overlap` | `50` | `LEX_AI_RAG__CHUNK_OVERLAP` | Token overlap between chunks |
| `enable_citations` | `True` | `LEX_AI_RAG__ENABLE_CITATIONS` | Include source citations in responses |
| `citation_style` | `inline` | `LEX_AI_RAG__CITATION_STYLE` | `inline`, `footnote`, or `numbered` |
| `enable_query_expansion` | `True` | `LEX_AI_RAG__ENABLE_QUERY_EXPANSION` | Expand queries before retrieval |
| `enable_hyde` | `False` | `LEX_AI_RAG__ENABLE_HYDE` | Hypothetical Document Embeddings |
| `synthesis_strategy` | `hybrid` | `LEX_AI_RAG__SYNTHESIS_STRATEGY` | `direct`, `extractive`, `abstractive`, `hybrid` |
| `tenancy.enabled` | `False` | — | Enable per-tenant pipeline isolation |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `RAGModule.configure(config)` | Production pipeline |
| `RAGModule.stub()` | In-memory / no-op pipeline for tests |

## Key Features

- **Multi-stage pipeline**: Ingestion, query processing, retrieval, context optimization, synthesis, quality assurance, post-processing
- **Chunking strategies**: recursive, semantic, token, fixed_size, sliding_window
- **Retrieval**: Vector search with `top_k` / `similarity_threshold` controls
- **Reranking**: FlashRank cross-encoder reranker
- **Synthesis**: Direct, extractive, abstractive, and hybrid synthesizers
- **HyDE support**: Hypothetical Document Embeddings for query expansion
- **Citations**: Inline, footnote, or numbered citation styles
- **Quality assurance**: Faithfulness check and hallucination detection

## Testing

```python
async with Application.boot(modules=[RAGModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/rag/module.py` | `RAGModule.configure()` and `RAGModule.stub()` |
| `src/lexigram/ai/rag/config.py` | `RAGConfig`, `RAGTenancyConfig`, `PipelineConfig`, all stage configs |
| `src/lexigram/ai/rag/di/provider.py` | `RAGProvider` — registers pipeline and supporting services |
| `src/lexigram/ai/rag/pipeline/` | Stage executor and pipeline runner |
| `src/lexigram/ai/rag/tenancy/` | `TenantScopedRAGPipeline` factory + resolver |
| `src/lexigram/ai/rag/exceptions.py` | Full exception hierarchy |
| `src/lexigram/ai/rag/types.py` | RAG-specific domain types |

## Multi-Tenancy

`lexigram-ai-rag` supports per-tenant pipeline isolation. When tenancy is
enabled, the provider registers a `TenantScopedRAGPipeline` — a caching
wrapper that builds a dedicated `RAGPipelineProtocol` per tenant, with a
tenant-resolved `collection_name`.

> **Note:** Enabling tenancy requires the app-wide `Context` binding, which
> ships with the core bootstrap module (`CoreModule` / `StandardModule` from
> `lexigram.app`). A bare `Application.boot(modules=[RAGModule...])` without
> it fails with `UnresolvableDependencyError: Context`.

### Configuration

```python
from lexigram.ai.rag import RAGModule
from lexigram.ai.rag.config import RAGConfig, RAGTenancyConfig

config = RAGConfig(
    tenancy=RAGTenancyConfig(enabled=True),
    collection_name="my_docs",
)
RAGModule.configure(config)
```

### Per-Tenant Collection Name

Use `RAGConfig.with_collection()` to create configs scoped to different
collection names — handy for dynamic per-tenant pipeline construction:

```python
tenant_config = RAGConfig().with_collection("tenant_a_collection")
```

### Components

| Component | Role |
|-----------|------|
| `RAGTenancyConfig` | Dataclass with `enabled` flag |
| `TenantScopedRAGPipeline` | Caches per-tenant pipelines (LRU eviction) |
| `TemplatedTenantCollectionResolver` | Resolves logical → physical collection name per tenant |
