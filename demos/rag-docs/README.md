# rag-docs — RAG over the framework's own docs

> Module name: `rag_docs` — run with `PYTHONPATH=demos/rag-docs/src uv run python -m rag_docs`

A fully offline, deterministic RAG pipeline. Markdown docs are loaded,
chunked, embedded with a BLAKE2b hashing embedder, stored in an in-memory
vector collection, retrieved through pluggable strategies, and synthesized
into cited answers — no LLM, no network.

## Lexigram concepts used

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace controllers/providers list |
| Module pattern | `WebModule.configure()` | Add your own modules |
| Provider lifecycle | `di/provider.py` | Replace with your registrations |
| Result<T,E> pattern | `controllers/api.py` | Return Result from handlers |
| Protocol binding | `repository/embedder.py` | Swap impl for real embedder |
| Constructor injection | Everywhere | Declare deps as typed params |
| Registry dispatch | `services/docs_ask.py` | Add strategies without if/elif |
| Domain models | `errors.py`, `services/` | Exception hierarchy + dataclasses |

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Deterministic embeddings | `repository/embedder.py` | `EmbeddingClientProtocol` — BLAKE2b + IDF |
| Corpus ingestion | `repository/index_builder.py` | `MarkdownLoader`, `MemoryVectorStore`, `VectorRecord` |
| Result-typed ask | `services/docs_ask.py` | `Result[AskAnswer, DocsAskError]` |
| Strategy registry | `services/docs_ask.py` | `Registry` — no if/elif dispatch |
| Cited synthesis | `services/docs_ask.py` | `ExtractiveSynthesizer(max_sentences=4)` |
| Error taxonomy | `errors.py` | `DocsAskError(RAGError)` → HTTP 400/404/502 |
| DI wiring | `di/provider.py` | `register()` (bind) vs `boot()` (ingest) |
| Split-screen UI | `ui/views/console.html` | Vanilla JS — no build step |

## Strategies

| Strategy | Behavior |
|----------|----------|
| `vector` (default) | Re-ranks candidates by embedding similarity score |
| `mmr` | Maximal Marginal Relevance — balances relevance vs redundancy (`lambda_param=0.7`) |

## Run it

From this demo's root (so `application.yaml` is discovered):

```bash
cd demos/rag-docs
PYTHONPATH=src uv run python -m rag_docs              # start server
PYTHONPATH=src uv run python -m rag_docs demo         # offline cited walkthrough
```

Open http://127.0.0.1:7075.  Type a question about Lexigram, pick a
strategy, and get cited answers from the framework's own docs.

Override the port without touching yaml: `LEX_WEB__SERVER__PORT=9000`.

The split-screen console gives you:

- **Left panel** — question input, strategy selector, run demo button,
  corpus stats (files/chunks), query history
- **Right panel** — answer with inline citations, loading skeleton

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/rag_docs/app.py` | Composition root: modules → providers → create_app |
| 2 | `src/rag_docs/main.py` | Lifecycle: `Application.boot()`, graceful shutdown |
| 3 | `src/rag_docs/di/provider.py` | `register()` (bind) vs `boot()` (ingest + assemble) |
| 4 | `src/rag_docs/repository/embedder.py` | BLAKE2b hashing embedder — protocol binding |
| 5 | `src/rag_docs/repository/index_builder.py` | Corpus ingestion pipeline |
| 6 | `src/rag_docs/services/docs_ask.py` | Domain service: embed → search → rerank → synthesize |
| 7 | `src/rag_docs/controllers/api.py` | Result-returning handlers → auto HTTP status mapping |
| 8 | `src/rag_docs/errors.py` | Error taxonomy — `DocsAskError(RAGError)` hierarchy |
| 9 | `src/rag_docs/ui/pages.py` | Page controller: serve HTML/assets only, no logic |

```
demos/rag-docs/
├── src/rag_docs/
│   ├── app.py                          # ⭐ composition root (start here)
│   ├── main.py                         # entry point / lifecycle
│   ├── __main__.py                     # python -m rag_docs
│   ├── errors.py                       # DocsAskError(RAGError) hierarchy
│   ├── di/
│   │   ├── __init__.py                 # DI wiring
│   │   └── provider.py                 # register() + boot() ingestion
│   ├── repository/
│   │   ├── embedder.py                 # BLAKE2b hashing embedder
│   │   └── index_builder.py            # walk → load → chunk → upsert
│   ├── services/
│   │   ├── __init__.py                 # re-exports
│   │   └── docs_ask.py                 # ask pipeline + strategy registry
│   ├── controllers/
│   │   └── api.py                      # POST /ask, GET /stats
│   └── ui/
│       ├── pages.py                    # page controller (HTML/assets)
│       ├── views/console.html          # split-screen console
│       └── static/
│           ├── app.js                  # vanilla JS client
│           └── style.css               # dark-theme split layout
├── application.yaml                    # web section (LEX_* overrides win)
└── tests/                              # 28 tests: API, pages, service, embedder, index
```

## Tests

```bash
uv run pytest demos/rag-docs/tests -q
```

Covers: both strategies' Ok paths, all three Err arms, citation format,
determinism (byte-identical answers), record identity/metadata, embedder
protocol compliance, corpus ingestion, page serving, and static assets.
