# RAG Pipeline Demo

Teaches the **Lexigram RAG pipeline pattern** — in-memory vector store,
document ingestion, retrieval, and context synthesis.  Demonstrates the
full RAG lifecycle without requiring external vector databases.

## What you'll learn

1. **Vector store** — in-memory vector storage with cosine similarity
2. **Document chunking** — splitting documents into indexable chunks
3. **Retrieval** — finding relevant documents for queries
4. **Context synthesis** — formatting retrieved documents for LLM context

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — vector dimension, chunk size, top-k |
| 2 | `src/ragdocs/app.py` | Composition root — `build_modules()` + `build_providers()` |
| 3 | `src/ragdocs/di/provider.py` | Provider lifecycle — `register()`, `boot()`, `health_check()` |
| 4 | `src/ragdocs/config.py` | Config model — `BaseConfig` + `Field()` with descriptions |
| 5 | `src/ragdocs/vector_store.py` | In-memory vector store — cosine similarity search |
| 6 | `src/ragdocs/services/chunker.py` | Document chunking — splitting by size |
| 7 | `src/ragdocs/services/retriever.py` | Retrieval — finding relevant documents |
| 8 | `src/ragdocs/controllers/api.py` | HTTP surface — thin controller adapters |
| 9 | `tests/` | Real composition root, no mocks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      application.yaml                           │
│  web: server/host/port, security/csrf/enabled                  │
│  ragdocs: collection_name, embedding_dimension, chunk_size, top_k│
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│  build_modules()  → [WebModule.configure(controllers=[...])]    │
│  build_providers() → [RagDocsProvider()]                        │
│  create_app()     → Application(name="rag-pipeline")           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      provider.py                                │
│  register(): container.singleton(RagDocsConfig, instance=cfg)  │
│  boot():     resolve config → create vector store → bind controller│
└─────────────────────────────────────────────────────────────────┘
```

## Quick start

```bash
cd demos/rag-pipeline
uv run python -m ragdocs
```

## Run tests

```bash
cd demos/rag-pipeline
uv run pytest tests/ -v
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/rag/ingest` | Ingest a document |
| `POST` | `/api/rag/search` | Search for similar documents |
| `POST` | `/api/rag/search/context` | Search and return formatted context |
| `GET` | `/api/rag/stats` | Get RAG pipeline statistics |
| `GET` | `/api/rag/health` | Health check |

## Switching to a real vector store

Replace `InMemoryVectorStore` in `provider.py` with a real backend:

```python
from lexigram.ai.rag import PineconeVectorStore, VectorConfig

vector_store = PineconeVectorStore(config=VectorConfig(index="my-index"))
```
