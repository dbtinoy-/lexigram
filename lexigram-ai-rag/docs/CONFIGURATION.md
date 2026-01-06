---
title: lexigram-ai-rag Configuration
description: All configuration keys for RAGConfig and PipelineConfig.
sidebar:
  order: 4
---

Configuration section: `ai.rag` (in `application.yaml`) or env prefix `LEX_AI_RAG__`.

The provider's `config_key = "ai.rag"` — a nested dot-separated key. The orchestrator reads `ai.rag:` from YAML and coerces it into `RAGConfig`.

---

## RAGConfig

Top-level configuration. Full example:

```yaml
ai.rag:
  enabled: true
  vector_store_type: pgvector
  vector_dimension: 1536
  collection_name: docs
  top_k: 5
  similarity_threshold: 0.7
  use_hybrid_search: true
  embedding_provider: openai
  embedding_model: text-embedding-3-small
  enable_citations: true
  citation_style: numbered
  chunk_size: 512
  chunk_overlap: 50
  chunking_strategy: recursive
  enable_query_expansion: true
  enable_hyde: false
  synthesis_strategy: hybrid
  enable_hallucination_detection: true
  enable_caching: true
  cache_ttl: 3600
```

Env-var override form (nested keys use `__`):

```bash
export LEX_AI_RAG__VECTOR_STORE_TYPE=qdrant
export LEX_AI_RAG__TOP_K=10
export LEX_AI_RAG__EMBEDDING_MODEL=text-embedding-3-large
```

### Field Reference

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AI_RAG__ENABLED` | Enable the RAG pipeline |
| `persist_directory` | `str \| None` | `None` | `LEX_AI_RAG__PERSIST_DIRECTORY` | Local directory for file-based stores (Chroma) |
| `vector_store_type` | `str` | `"pgvector"` | `LEX_AI_RAG__VECTOR_STORE_TYPE` | Backend: `pgvector`, `chroma`, `qdrant`, `mock` |
| `vector_dimension` | `int` | `1536` | `LEX_AI_RAG__VECTOR_DIMENSION` | Embedding dimension (1536 for ada-002) |
| `collection_name` | `str` | `"default"` | `LEX_AI_RAG__COLLECTION_NAME` | Collection/index name |
| `top_k` | `int` | `5` | `LEX_AI_RAG__TOP_K` | Number of documents to retrieve |
| `similarity_threshold` | `float` | `0.7` | `LEX_AI_RAG__SIMILARITY_THRESHOLD` | Minimum similarity score (0–1) |
| `use_hybrid_search` | `bool` | `True` | `LEX_AI_RAG__USE_HYBRID_SEARCH` | Enable hybrid (semantic + keyword) |
| `embedding_provider` | `str` | `"openai"` | `LEX_AI_RAG__EMBEDDING_PROVIDER` | Provider: `openai`, `cohere`, etc. |
| `embedding_model` | `str \| None` | `None` | `LEX_AI_RAG__EMBEDDING_MODEL` | **Must be set explicitly** |
| `enable_citations` | `bool` | `True` | `LEX_AI_RAG__ENABLE_CITATIONS` | Include source citations in responses |
| `citation_style` | `str` | `"inline"` | `LEX_AI_RAG__CITATION_STYLE` | `inline`, `footnote`, `numbered` |
| `min_citation_confidence` | `float` | `0.6` | `LEX_AI_RAG__MIN_CITATION_CONFIDENCE` | Min confidence for citations (0–1) |
| `chunk_size` | `int` | `512` | `LEX_AI_RAG__CHUNK_SIZE` | Text chunk size in tokens |
| `chunk_overlap` | `int` | `50` | `LEX_AI_RAG__CHUNK_OVERLAP` | Overlap between consecutive chunks |
| `chunking_strategy` | `str` | `"recursive"` | `LEX_AI_RAG__CHUNKING_STRATEGY` | `recursive`, `semantic`, `token` |
| `enable_query_expansion` | `bool` | `True` | `LEX_AI_RAG__ENABLE_QUERY_EXPANSION` | Enable query expansion |
| `enable_hyde` | `bool` | `False` | `LEX_AI_RAG__ENABLE_HYDE` | Enable HyDE |
| `synthesis_strategy` | `str` | `"hybrid"` | `LEX_AI_RAG__SYNTHESIS_STRATEGY` | `direct`, `extractive`, `abstractive`, `hybrid` |
| `enable_hallucination_detection` | `bool` | `True` | `LEX_AI_RAG__ENABLE_HALLUCINATION_DETECTION` | Check for hallucinations |
| `enable_caching` | `bool` | `True` | `LEX_AI_RAG__ENABLE_CACHING` | Cache RAG query results |
| `cache_ttl` | `int` | `3600` | `LEX_AI_RAG__CACHE_TTL` | Cache TTL in seconds |

---

## PipelineConfig

```python
from lexigram.ai.rag.config import PipelineConfig

config = PipelineConfig(
    name="my-pipeline",
    stages=["RETRIEVAL", "SYNTHESIS", "QUALITY_ASSURANCE"],
    max_retries=3,
    require_citations=True,
    auto_evaluate_every_n=100,
)
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | `"default-rag-pipeline"` | Pipeline identifier |
| `stages` | `list[PipelineStageType]` | `[RETRIEVAL, SYNTHESIS, QUALITY_ASSURANCE]` | Ordered pipeline stages |
| `max_retries` | `int` | `3` | Retries per stage on transient failure |
| `retry_delay` | `float` | `1.0` | Delay between retries (seconds) |
| `default_error_strategy` | `str` | `"graceful"` | `graceful`, `fail_fast`, `skip` |
| `require_citations` | `bool` | `False` | Raise `MissingCitationsError` if no citations |
| `auto_evaluate_every_n` | `int \| None` | `None` | Auto-evaluation frequency |

Sub-configs (`ingestion`, `query_processing`, `retrieval`, `context_optimization`, `synthesis`, `quality_assurance`, `post_processing`) each expose their own fields. See `lexigram.ai.rag.config` for the full schema.

---

## Environment Variables

All keys map from env vars using `LEX_AI_RAG__` prefix with `__` as nested delimiter:

```
LEX_AI_RAG__ENABLED=true
LEX_AI_RAG__VECTOR_STORE_TYPE=qdrant
LEX_AI_RAG__EMBEDDING_MODEL=text-embedding-3-small
LEX_AI_RAG__CHUNK_SIZE=1024
LEX_AI_RAG__USE_HYBRID_SEARCH=false
```
