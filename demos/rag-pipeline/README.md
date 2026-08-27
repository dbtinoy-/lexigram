# RAG Pipeline Demo

Teaches Lexigram RAG pipeline pattern — in-memory vector store, document
ingestion, retrieval, and synthesis.

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — RAG pipeline settings |
| 2 | `src/ragdocs/app.py` | Composition root — module wiring |
| 3 | `src/ragdocs/di/provider.py` | Provider lifecycle — register, boot, shutdown |
| 4 | `src/ragdocs/vector_store.py` | In-memory vector store implementation |
| 5 | `src/ragdocs/services/` | Document chunking and retrieval patterns |
| 6 | `tests/` | Real composition root, no mocks |

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
