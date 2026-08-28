# RAG Pipeline Demo

A focused, browser-first example of **Lexigram VectorModule** for document
chunking and retrieval. Lexigram owns vector-store lifecycle, collection
management, and similarity search. The demo supplies only chunking and a
repeatable local embedder, so it runs without an external model or database.

## What you'll learn

1. `VectorModule.stub()` — real `VectorStoreProtocol` DI wiring
2. Collection lifecycle — create a dimensioned cosine/flat collection at boot
3. Document chunking — turn one document into indexable records
4. Vector upsert and search — use Lexigram's collection protocol directly
5. Context synthesis — format ranked sources for an LLM prompt

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Collection, dimension, chunk-size, and top-k settings |
| 2 | `src/ragdocs/app.py` | `VectorModule` + `WebModule` composition |
| 3 | `src/ragdocs/di/provider.py` | Resolve the store and create the collection |
| 4 | `src/ragdocs/vector_store.py` | Standalone deterministic embedding adapter |
| 5 | `src/ragdocs/services/chunker.py` | Document preprocessing |
| 6 | `src/ragdocs/services/retriever.py` | `SearchQuery` and collection search |
| 7 | `src/ragdocs/controllers/api.py` | Ingest, search, and context endpoints |
| 8 | `tests/` | Real composition-root coverage |

## Architecture

```
VectorModule.stub() ──► VectorStoreProtocol ──► collection
                                                   │
                         chunker + embedder ◄─────┘
                                                   │
                                                   ▼
                                       browser retrieval console
```

The deterministic embedder is intentionally the only local substitute. To
move to a real vector backend, change the module configuration; the controller
and retriever continue to depend on Lexigram contracts.

## Quick start

```bash
cd demos/rag-pipeline
uv run python -m ragdocs
```

Open the URL printed by the server, ingest a document, and search it.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/rag/ingest` | Chunk and upsert a document |
| `POST` | `/api/rag/search` | Search the Lexigram collection |
| `POST` | `/api/rag/search/context` | Return ranked context and sources |
| `GET` | `/api/rag/stats` | Show collection and retrieval stats |
| `GET` | `/api/rag/health` | Show collection readiness |
