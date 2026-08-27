# Spec: `rag-docs` — RAG demo over the framework's own docs

**Status:** approved concept (user picked "rag-docs" with a strategy-comparison act)
**Date:** 2026-08-21
**Demo dir:** `demos/rag-docs/`

## Purpose

A fifth in-repo demo teaching the complete RAG stack of the Lexigram
framework: document loading, chunking, embedding, vector search,
retrieval strategies, and cited answer synthesis. It follows the four
existing demos' contract: runnable offline, deterministic, gated like the
framework.

## User-visible behavior

CLI (mirrors the orders demo's subcommand style):

```bash
uv run python -m rag_docs index                     # build + print corpus stats
uv run python -m rag_docs ask "how do modules export services?"
uv run python -m rag_docs ask --strategy mmr "how do modules export services?"
uv run python -m rag_docs demo                      # index + canned questions
```

- **Every command builds the index at boot** — the vector store is memory-only
  by design (see non-goals), so a standalone `ask` would otherwise query an
  empty store across the process boundary. `index` exists to print corpus
  stats (files, chunks, timing); it shares the same boot path.
- `ask` prints the synthesized answer followed by numbered citations of the
  form `[n] <relative-path>#<chunk-index>`.
- `--strategy` selects the retrieval strategy: `vector` (default) or `mmr`.
- `--docs-dir` overrides the corpus location; default is the repository's
  real `docs/` tree, resolved relative to the demo package location (never
  the process CWD).
- Exit code is non-zero on indexing or query failure; errors print as
  `error: <message>`.

## Functional requirements

1. **Corpus ingestion** — walk `<docs-dir>/**/*.md`, load each file with the
   framework `MarkdownLoader`, chunk each loaded section with
   `create_chunker(ChunkingStrategy.RECURSIVE, ChunkingConfig(chunk_size=800, overlap=120))`,
   embed every chunk, and upsert into an in-memory vector collection named
   `lexigram-docs`.
2. **Record identity** — each `VectorRecord.id` is `<relative-path>#<chunk_index>`;
   metadata carries `source` (relative path), `chunk_index`, and `title`
   (first `# `-heading of the file, or the file name).
3. **Deterministic embeddings** — a stdlib-only `HashingEmbedder` implementing
   the framework's `EmbeddingClientProtocol`
   (`async embed(texts: list[str]) -> list[list[float]]`,
   `core/lexigram-contracts/.../ai/llm.py:147`): BLAKE2b token hashing,
   dimension 1024, L2-normalized; signed hashing (±1) so collisions cancel; light suffix stemming; corpus-fitted smoothed IDF with a df-ratio stopword rule (active only for corpora ≥ 20 texts). Same text always produces the same vector,
   across processes.
4. **Retrieval strategies** — `vector` (`VectorRetrievalStrategy`) and `mmr`
   (`MMRRetrievalStrategy(lambda_param=0.7)`), selected by name through a
   dict-based registry injected via DI (no if/elif dispatch). Both exist in
   `lexigram-ai-rag` with a name registry
   (`retrieval/strategy_registry.py`) — reuse it or mirror its shape.
5. **Synthesis** — `ExtractiveSynthesizer(max_sentences=4)` produces the
   answer from retrieved candidates; no LLM, no network. Its
   `async synthesize(...) -> Result[RAGResponse, RAGError]` contract is the
   Err source for requirement 6.
6. **Result-typed domain op** — `DocsAskService.ask(query, strategy) ->
   Result[AskAnswer, DocsAskError]`, where `DocsAskError(RAGError)` extends
   the contracts base (`lexigram.contracts.ai.exceptions.RAGError`) and leaf
   errors extend it:
   - `Err(NoResultsError)` when the corpus is empty or nothing matches,
   - `Err(UnknownStrategyError)` for an unregistered strategy name,
   - `Err(SynthesisFailedError)` when the synthesizer returns `Err`.
7. **Reproducibility** — identical corpus + identical query produce byte-
   identical answers (locked down by tests).
8. **Wiring** — own `DocsAskProvider` + `DocsAskModule` following the
   resilient-rates shape: provider registers `HashingEmbedder`, strategy
   registry, and `DocsAskService` as singletons; no framework module imports
   are required (loader/chunker/synthesizer are libraries constructed inside
   the provider), so container resolution covers the three singletons only.

## Non-goals

- No live LLM/embedding API calls anywhere in the demo.
- No persistence beyond process lifetime (memory backend by design).
- No web controllers/SSE (realtime-monitor already teaches that).

## Global constraints

- Python 3.11+ syntax, absolute imports, `from __future__ import annotations` everywhere.
- Google-style docstrings; typed constructors; no `Any` on injected deps.
- Enums only as `str, Enum` / `StrEnum`; registry-based dispatch, no if/elif chains.
- Files under 700 lines; ruff + format clean under root config
  (`demos/**` per-file ignores already cover T201/INP001/ANN).
- All I/O async; store task references (RUF006) if any background tasks appear.
- Tests run offline: `uv run --group tooling pytest demos/rag-docs/tests -q`.

## Tests (required cases)

1. Determinism: same corpus + query ⇒ byte-identical answer and citations, re-run twice in-process.
2. `vector` and `mmr` strategies both return Ok with ≥1 citation; mmr respects `lambda_param=0.7` construction.
3. Unknown strategy name ⇒ `Err(UnknownStrategyError)`.
4. Empty corpus dir ⇒ `Err(NoResultsError)`; no-match gibberish query ⇒ `Err(NoResultsError)`.
5. Citation format: every citation matches `<relative-path>#<int>` and cites a real chunk id from the store.
6. Record identity/metadata: id format, `source`, `chunk_index`, `title` (first `# ` heading or file name).
7. CLI smoke via `_build_parser` + `_run` + captured stdout: `demo` prints answers + `[n] path#chunk` citations; unknown strategy exits non-zero printing `error: ...`.
8. HashingEmbedder contract: implements `EmbeddingClientProtocol`; L2 norm ≈ 1.0; dimension 256; same text ⇒ identical vector.

## Acceptance criteria

- [ ] Gates wired in the same change set: `Makefile` (`DEMO_TEST_DIRS`,
      `DEMO_COMPILE_DIRS`), `.github/workflows/ci.yml` Demos-gate pytest
      step, and `demos/README.md` listing the fifth demo.
- [ ] `make check-demos` fully green — all five demo suites pass
      (resilient-rates is merged and green; no exclusions).
- [ ] `python -m rag_docs demo` runs end to end against the real `docs/`
      tree printing answers + citations.
- [ ] Same-seed determinism test proves byte-identical answers on re-run.
