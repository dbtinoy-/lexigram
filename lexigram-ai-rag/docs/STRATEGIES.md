---
title: lexigram-ai-rag Strategies
description: Chunking, retrieval, and synthesis strategies — when to use each and how to create custom ones.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Strategy overview

RAG pipelines break down into three strategic decisions: **how to chunk** documents, **how to retrieve** relevant context, and **how to synthesise** the final answer. Each layer has multiple strategies registered in type-specific registries.

## Chunking strategies

Chunking splits documents into manageable pieces for embedding and retrieval. Built-in strategies are registered in `ChunkingStrategyRegistry`.

| Strategy | Class | Best for |
|----------|-------|----------|
| **Fixed** (`FIXED_SIZE`) | `FixedSizeChunker` | Uniform documents with consistent structure (logs, records) |
| **Semantic** (`SEMANTIC`) | `SemanticChunker` | Natural language where sentence/paragraph boundaries matter |
| **Recursive** (`RECURSIVE`) | `RecursiveChunker` | Mixed content — recursively splits by separator priority |
| **Token** (`TOKEN`) | `TokenChunker` | Precise token budgeting for LLM context windows |
| **Sliding window** (`SLIDING_WINDOW`) | `SlidingWindowChunker` | Overlapping context for sequential reasoning |

```python
from lexigram.ai.rag.chunking.strategy_registry import ChunkingStrategyRegistry
from lexigram.ai.rag.chunking.types import ChunkingStrategy

registry = ChunkingStrategyRegistry.with_defaults()
chunker = registry.create_chunker(
    strategy=ChunkingStrategy.RECURSIVE,
    chunk_size=512,
    overlap=50,
)
chunks = chunker.chunk("Long document text...")
```

### When each applies

- **Fixed**: Same-size chunks for tabular data. Fastest but ignores semantics.
- **Semantic**: Uses sentence embeddings to detect topic boundaries. Best for prose, articles, documentation.
- **Recursive**: Default choice. Tries separators (`\n\n`, `\n`, `.`, ` `) in order. Works well for most text.
- **Token**: Counts tokens precisely via model-specific encoders. Essential for fitting within LLM context limits.
- **Sliding window**: Retains surrounding context across chunk boundaries. Useful for narrative text where context spans chunk edges.

## Retrieval strategies

Retrieval strategies rank candidate documents by relevance. Built-in strategies are registered in `RetrievalStrategyRegistry`.

| Strategy | Key | Class | Behavior |
|----------|-----|-------|----------|
| **Vector (similarity)** | `"vector"` | `VectorRetrievalStrategy` | Cosine/IP similarity against query embedding |
| **MMR (diversity)** | `"mmr"` | `MMRRetrievalStrategy` | Maximum Marginal Relevance — balances relevance and diversity |
| **Hybrid (RRF)** | Via config | Retrieval config | Reciprocal Rank Fusion — combines vector + keyword scores |

```python
from lexigram.ai.rag.retrieval.strategy_registry import RetrievalStrategyRegistry

registry = RetrievalStrategyRegistry.with_defaults()
strategy = registry.instantiate("mmr", lambda_param=0.7)
results = await strategy.retrieve(query, candidates, top_k=5)
```

### When each applies

- **Similarity**: Direct semantic search. Best when the answer is semantically close to the query.
- **Hybrid (RRF)**: Combines semantic (embedding) and keyword (BM25) scores via reciprocal rank fusion. Best for general-purpose retrieval — more robust than pure similarity.
- **Multi-vector**: Uses multiple embeddings per document (e.g., summary + full text). Improves retrieval for long documents.
- **Parent-document**: Retrieves smaller chunks but returns the parent document as context. Useful when chunk boundaries might split relevant content.

Configure hybrid search in `RAGConfig`:

```python
from lexigram.ai.rag.config import RAGConfig

config = RAGConfig(
    use_hybrid_search=True,
    top_k=5,
    similarity_threshold=0.7,
)
```

## Synthesis strategies

Synthesis combines retrieved context into a final response. Built-in strategies are registered in `SynthesisStrategyRegistry`.

| Strategy | Class | Behavior |
|----------|-------|----------|
| **Direct** | `DirectSynthesizer` | Concatenates context chunks |
| **Extractive** | `ExtractiveSynthesizer` | Extracts relevant sentences from context |
| **Abstractive** | `AbstractiveSynthesizer` | LLM generates new text grounded in context |
| **Hybrid** | `HybridSynthesizer` | Extractive + abstractive combined |

```python
from lexigram.ai.rag.pipeline.stages.synthesis_registry import (
    SynthesisStrategyRegistry,
    DirectSynthesisStrategyHandler,
    AbstractiveSynthesisStrategyHandler,
)

registry = SynthesisStrategyRegistry.with_defaults()
synthesizer = registry.create_synthesizer(
    strategy=SynthesisStrategy.HYBRID,
    config=synthesis_config,
    llm_client=llm_client,
)
```

### When each applies

- **Direct**: No LLM call needed. Fastest, lowest cost. Use for simple extractive QA.
- **Extractive**: Picks existing sentences. Good for factoid QA where verbatim answers matter.
- **Abstractive**: Uses LLM to paraphrase and synthesise. Best for summarisation, explanation, complex reasoning.
- **Hybrid**: Extracts key passages then LLM synthesises. Balances faithfulness and fluency. Default recommendation.

## Strategy registry pattern

All strategies follow the same registry pattern:

```python
from lexigram.primitives.registry import StrategyRegistry

class MyStrategyRegistry(StrategyRegistry):
    def __init__(self) -> None:
        super().__init__(name="my.strategies", allow_overwrite=True)

    @classmethod
    def with_defaults(cls) -> MyStrategyRegistry:
        registry = cls()
        registry.register("strategy_a", StrategyAImpl)
        registry.register("strategy_b", StrategyBImpl)
        return registry
```

- Registries start **empty** in `__init__`
- Pre-populated via `with_defaults()` classmethod
- `RAGProvider.register()` calls `with_defaults()` on each registry

## Creating custom strategies

### Custom chunker

```python
from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk

class MyChunker(AbstractChunker):
    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        # Custom chunking logic
        return [Chunk(text=text[i:i+100], metadata=metadata or {}) for i in range(0, len(text), 100)]

# Register it
from lexigram.ai.rag.chunking.types import ChunkingStrategy
registry = ChunkingStrategyRegistry()
registry.register("my_custom", MyChunker)
```

### Custom retrieval strategy

Implement `RetrievalStrategyProtocol`:

```python
from lexigram.contracts.ai.rag import RetrievalStrategyProtocol

class MyRetrievalStrategy(RetrievalStrategyProtocol):
    async def retrieve(self, query: str, candidates: list, top_k: int) -> list:
        # Custom ranking logic
        return sorted(candidates, key=lambda c: c.score, reverse=True)[:top_k]
```

### Custom synthesis

Register a handler in `SynthesisStrategyRegistry`:

```python
from lexigram.ai.rag.pipeline.stages.synthesis_registry import (
    SynthesisStrategyHandler,
    SynthesisStrategyRegistry,
)

class MySynthesisHandler(SynthesisStrategyHandler):
    def can_handle(self, strategy) -> bool:
        return strategy == "compressive"

    def create_synthesizer(self, config, llm_client):
        return MyCompressiveSynthesizer(llm_client)

registry = SynthesisStrategyRegistry.with_defaults()
registry.register(MySynthesisHandler())
```

## See also

- `RAGConfig` — top-level config (chunk_size, chunking_strategy, retrieval settings)
- `ChunkingStrategyRegistry` — chunker registration and instantiation
- `RetrievalStrategyRegistry` — retrieval strategy registration
- `SynthesisStrategyRegistry` — synthesis handler registration
- `RAGProvider` — wires all registries on boot
