# Rag Docs Demo

Demonstrates the **RAG subsystem** of Lexigram over the framework's own
documentation.

This demo is a small retrieval-augmented question answering pipeline built
entirely from framework pieces: markdown documents are loaded and chunked,
embedded with a deterministic hashing embedder, stored in an in-memory vector
collection, retrieved through pluggable strategies (`vector` or `mmr`), and
synthesized into cited answers — no LLM, no network, fully deterministic.

## REST API

```bash
uv run python -m rag_docs serve         # :7075 (RAGDOCS_PORT)
curl -X POST localhost:7075/ask -H 'content-type: application/json' \
     -d '{"question":"how do modules export services?"}'
curl localhost:7075/stats               # corpus files/chunks
```


## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Deterministic embeddings | `src/rag_docs/embedder.py` | `EmbeddingClientProtocol` implemented stdlib-only |
| Corpus ingestion (walk → load → chunk → upsert) | `src/rag_docs/index_builder.py` | `MarkdownLoader`, `create_chunker(ChunkingStrategy.RECURSIVE, ...)`, `MemoryVectorStore`, `VectorRecord` |
| Result-typed domain op | `src/rag_docs/service.py` | `Result[AskAnswer, DocsAskError]` (`Ok`/`Err`) |
| Retrieval strategy registry | `src/rag_docs/service.py` | `VectorRetrievalStrategy`, `MMRRetrievalStrategy(lambda_param=0.7)` |
| Cited extractive synthesis | `src/rag_docs/service.py` | `ExtractiveSynthesizer(max_sentences=4)` |
| Error taxonomy | `src/rag_docs/errors.py` | `DocsAskError(RAGError)` from contracts bases |
| DI wiring | `src/rag_docs/di/provider.py`, `module.py` | `Provider`, `@module` lazy-factory pattern |
| CLI | `src/rag_docs/main.py` | `Application.boot()` + container resolution |

## Run it

```bash
uv run python -m rag_docs demo
```

`demo` builds the index from the repository's real `docs/` tree and asks
three canned questions across both strategies, printing an extractive answer
plus numbered citations of the form `[n] <path>#<chunk>`.

You can also drive each piece yourself:

```bash
uv run python -m rag_docs index                                 # corpus stats
uv run python -m rag_docs ask "how do modules export services?"
uv run python -m rag_docs ask --strategy mmr "what is the result pattern?"
```

Every command rebuilds the index at boot — the store is memory-only by
design, so state never crosses process boundaries. `--docs-dir` overrides
the corpus location.

## Strategies

| Strategy | Behavior |
|----------|----------|
| `vector` (default) | Re-ranks candidates by embedding similarity score |
| `mmr` | Maximal Marginal Relevance — balances relevance against redundancy (`lambda_param=0.7`) |

## Layout

```
demos/rag-docs/
├── src/rag_docs/
│   ├── embedder.py        # HashingEmbedder (BLAKE2b buckets, dim 256)
│   ├── errors.py          # DocsAskError(RAGError) + leaves
│   ├── index_builder.py   # walk → MarkdownLoader → chunk → upsert
│   ├── service.py         # DocsAskService: search → strategy → synthesis
│   ├── di/provider.py     # DocsAskProvider (index at boot)
│   ├── module.py          # DocsAskModule
│   └── main.py            # CLI: index / ask / demo
└── tests/                 # pytest suite (offline, deterministic)
```

## Tests

```bash
uv run pytest demos/rag-docs/tests -q
```

The suite boots the real module graph, ingests fixture corpora, and asserts
determinism (byte-identical answers on re-run), both strategies' Ok paths,
all three Err arms, citation format, record identity/metadata, and the
embedder contract.
