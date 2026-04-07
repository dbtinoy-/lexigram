---
title: lexigram-ai-rag How-Tos
description: Task-oriented recipes for common RAG workflows.
sidebar:
  order: 5
---

## Configure a Custom RAG Pipeline

```python
from lexigram.ai.rag import RAGModule, RAGConfig
from lexigram.ai.rag.config import PipelineConfig

config = RAGConfig(
    vector_store_type="qdrant",
    collection_name="knowledge_base",
    top_k=10,
    enable_citations=True,
    citation_style="numbered",
)

pipeline_cfg = PipelineConfig(
    stages=["QUERY_PROCESSING", "RETRIEVAL", "CONTEXT_OPTIMIZATION", "SYNTHESIS", "QUALITY_ASSURANCE"],
    require_citations=True,
)

module = RAGModule.configure(config)
```

## Add a Custom Chunking Strategy

```python
from lexigram.ai.rag.chunking import create_chunker
from lexigram.ai.rag.chunking.types import Chunk

# Built-in strategies
chunker = create_chunker("semantic", chunk_size=512, chunk_overlap=50)
chunks = chunker.chunk("Long document text here...")
```

## Use Hybrid Search

Hybrid search combines semantic vector similarity with BM25 keyword scoring:

```python
config = RAGConfig(
    vector_store_type="pgvector",
    use_hybrid_search=True,
    top_k=10,
)
```

When enabled, retrieval runs vector and keyword searches in parallel and fuses results via Reciprocal Rank Fusion (RRF).

## Handle Pipeline Results Correctly

```python
from lexigram.ai.rag.exceptions import RetrievalError, SynthesisError

result = await pipeline.execute(RAGContext(query="What's new?"))
match result:
    case Ok(response):
        print(f"Answer: {response.answer}")
        print(f"Confidence: {response.confidence}")
        for i, c in enumerate(response.citations or []):
            print(f"  [{i + 1}] {c}")
    case Err(RetrievalError() as e):
        logger.error("Retrieval failed — check vector store connection", error=str(e))
    case Err(SynthesisError() as e):
        logger.error("Synthesis failed — check LLM provider", error=str(e))
    case Err(e):
        logger.error("RAG pipeline failed", error=str(e))
```

## Enable Hallucination Detection

```python
config = RAGConfig(
    enable_hallucination_detection=True,
)

# Stricter checks via PipelineConfig
from lexigram.ai.rag.config import PipelineConfig
pipeline_cfg = PipelineConfig(
    quality_assurance__min_faithfulness=0.8,
    quality_assurance__reject_low_quality=True,
)
```

## Use Citations in Production

```python
config = RAGConfig(
    enable_citations=True,
    citation_style="numbered",  # inline, footnote, or numbered
    min_citation_confidence=0.7,
)

# In PipelineConfig, enforce citations
pipeline_cfg = PipelineConfig(require_citations=True)
# MissingCitationsError raised if no citations in response
```

## Custom Retrieval via Entry Points

Create a provider that implements `RetrievalStrategyProtocol` and register it under the `lexigram.retrieval.strategies` entry-point group:

```python
# my_package/strategies.py
from lexigram.contracts.ai.rag import RetrievalStrategyProtocol

class CustomRetrieval(RetrievalStrategyProtocol):
    async def retrieve(self, query, candidates, *, top_k=5, **kwargs):
        # Custom ranking logic
        ...
```

```toml
# pyproject.toml
[project.entry-points."lexigram.retrieval.strategies"]
custom = "my_package.strategies:CustomRetrieval"
```

## Test with a Mock Vector Store

```python
config = RAGConfig(vector_store_type="mock")
async with Application.boot(
    name="test-rag",
    modules=[RAGModule.configure(config)],
) as app:
    pipeline = await app.container.resolve(RAGPipelineProtocol)
    result = await pipeline.execute(RAGContext(query="test"))
    assert result.is_ok()
```
