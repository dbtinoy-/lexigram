---
title: lexigram-ai-rag Guide
description: Retrieval-Augmented Generation — chunking, retrieval, synthesis, citations.
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-llm` | Optional | LLM-based synthesis |
| `lexigram-vector` | Optional | Vector store integration |

`lexigram-ai-rag` provides a modular, async RAG pipeline that retrieves relevant context from a knowledge base and synthesises it into grounded answers with citations.

## The Problem

LLMs hallucinate. Their training data is static and doesn't include your documents. A RAG pipeline solves this by:

1. **Indexing** — chunking and embedding your documents into a vector store.
2. **Retrieving** — given a query, finding the most relevant chunks.
3. **Synthesising** — feeding the retrieved context to an LLM to produce a grounded, cited answer.

## Mental Model

The pipeline is a series of composable stages, each swappable via strategy registries:

```
Query → Query Processing → Retrieval → Reranking → Synthesis → Quality Assurance → Answer
```

Each stage is optional and configured via `PipelineConfig.stages`. The default stages are `RETRIEVAL`, `SYNTHESIS`, and `QUALITY_ASSURANCE`.

---

## Core Concepts

### RAGConfig

Top-level configuration for the pipeline — vector store backend, chunking parameters, retrieval settings, citation style, and caching. Injected automatically when the provider has `config_key = "ai.rag"`.

### Pipeline Stages

Each stage is a named step in the execution graph. Stages are ordered, so `RETRIEVAL` always runs before `SYNTHESIS`. Available stages:

| Stage | Purpose |
|-------|---------|
| `INGESTION` | Document loading, chunking, and indexing |
| `QUERY_PROCESSING` | Query expansion, HyDE, routing |
| `RETRIEVAL` | Vector + keyword search, multi-hop |
| `CONTEXT_OPTIMIZATION` | Reranking, compression, deduplication |
| `SYNTHESIS` | Answer generation from retrieved context |
| `QUALITY_ASSURANCE` | Faithfulness, relevance, hallucination checks |
| `POST_PROCESSING` | Caching, metrics, logging |

### Strategy Registries

Plug in custom behaviour by registering strategies. Each registry has `with_defaults()`:

- `ChunkingStrategyRegistry` — `recursive`, `semantic`, `token`, `fixed_size`
- `RetrievalStrategyRegistry` — retrieval strategies
- `RerankingStrategyRegistry` — `cross-encoder`, `FlashRank` (optional)
- `CompressionStrategyRegistry` — `LLMLingua-2` (optional)
- `HyDEStrategyRegistry` — hypothetical document embedding generators
- `ReasoningStrategyRegistry` — multi-step reasoning strategies
- `SynthesisStrategyRegistry` — `direct`, `extractive`, `abstractive`, `hybrid`

### Result Pattern

The pipeline's `execute()` method returns `Result[RAGResponse, RAGError]`. Always check both cases:

```python
result = await pipeline.execute(RAGContext(query="What is Lexigram?"))
if result.is_ok():
    response = result.unwrap()
    print(f"Answer: {response.answer}")
    print(f"Sources: {len(response.sources)} documents")
    print(f"Confidence: {response.confidence}")
else:
    error = result.unwrap_err()
    match error:
        case RetrievalError():
            logger.error("retrieval_failed", error=str(error))
        case SynthesisError():
            logger.error("synthesis_failed", error=str(error))
        case _:
            logger.error("rag_failed", error=str(error))
```

---

## Typical Usage

### Full Pipeline with Custom Config

```python
import asyncio
from lexigram import Application
from lexigram.ai.rag import RAGModule, RAGConfig, PipelineConfig


async def main() -> None:
    config = RAGConfig(
        vector_store_type="pgvector",
        collection_name="docs",
        top_k=10,
        chunk_size=1024,
        chunk_overlap=128,
        enable_citations=True,
        citation_style="numbered",
        enable_hallucination_detection=True,
        embedding_model="text-embedding-3-small",
    )

    async with Application.boot(
        name="rag-app",
        modules=[RAGModule.configure(config)],
        config_path="application.yaml",
    ) as app:
        pipeline = await app.container.resolve(RAGPipelineProtocol)
        result = await pipeline.execute(
            RAGContext(
                query="How do I configure RAG?",
                filters={"department": "engineering"},
            )
        )
        if result.is_ok():
            response = result.unwrap()
            print(f"Confidence: {response.confidence:.2f}")
            for i, source in enumerate(response.citations or []):
                print(f"  [{i + 1}] {source}")
```

### Using a Custom Chunking Strategy

```python
from lexigram.ai.rag.chunking.strategy_registry import ChunkingStrategyRegistry

registry = ChunkingStrategyRegistry.with_defaults()
# Add a custom chunker
registry.register("markdown", MarkdownHeaderChunker())

# Pass to the provider via config
config = RAGConfig(chunking_strategy="markdown")
```

---

## Integration

`lexigram-ai-rag` communicates with other packages through contracts in `lexigram-contracts`:

| Protocol | Used for | Resolved by |
|----------|----------|-------------|
| `RAGPipelineProtocol` | Pipeline execution (this package) | `RAGProvider` |
| `RetrievalStrategyProtocol` | Retrieval/reranking strategies | `RAGProvider` |
| `SynthesizerProtocol` | LLM-based answer generation | `lexigram-ai-llm` (optional) |
| `WorkingMemoryProtocol` | Conversation memory context | `lexigram-ai-memory` (optional) |
| `GraphStoreProtocol` | Knowledge graph enhancement | `lexigram-graph` (optional) |

The provider boot phase resolves optional bindings. If none exist, pipeline stages fall back gracefully.

---

## Best Practices

- ✅ Set `embedding_model` explicitly — it has no vendor-specific default.
- ✅ Enable `hallucination_detection` in production.
- ✅ Use `require_citations=True` in `PipelineConfig` for regulated domains.
- ✅ Match `vector_dimension` to your embedding model's output dimension.
- ✅ Configure `cache_ttl` based on how often your document set changes.
- ❌ Don't use `result.unwrap()` without checking `is_ok()` — retrieval can fail.
- ❌ Don't set `vector_store_type="mock"` in production.
- ❌ Don't exceed `top_k=50` without performance testing.

---

## Next Steps

- [Architecture](./ARCHITECTURE.md) — provider lifecycle, contracts, extension points
- [Configuration](./CONFIGURATION.md) — all config keys
- [How-Tos](./HOWTOS.md) — custom strategies, multimodal, citations
- [Troubleshooting](./TROUBLESHOOTING.md) — common errors
