---
title: lexigram-ai-rag Troubleshooting
description: Common errors, causes, and fixes.
sidebar:
  order: 6
---

## `RetrievalError` — Document retrieval failed

**Exception:** `lexigram.contracts.ai.rag.RetrievalError`

**Cause:** Vector store is unreachable, the collection doesn't exist, or the query embedding failed.

**Fix:**
- Verify the vector store backend is running and configured correctly.
- Check `collection_name` matches an existing collection.
- Ensure `embedding_model` is set and accessible.
- Confirm `vector_dimension` matches your embedding model's output.

## `SynthesisError` — Answer synthesis failed

**Exception:** `lexigram.contracts.ai.rag.SynthesisError`

**Cause:** The LLM call during the synthesis stage failed — network error, rate limit, or content filter.

**Fix:**
- Check the LLM provider is configured and has available quota.
- Verify the API key is valid.
- Reduce `top_k` or chunk sizes if context exceeds the model's token limit.

## `MissingCitationsError` — No citations in response

**Exception:** `lexigram.ai.rag.exceptions.MissingCitationsError`

**Cause:** `PipelineConfig.require_citations=True` but the synthesizer produced no citations.

**Fix:**
- Ensure `enable_citations=True` in `RAGConfig`.
- Verify retrieved documents contain source metadata.
- Set `min_citation_confidence` lower if documents have low relevance scores.
- Disable `require_citations` if citations aren't critical for this pipeline.

## `PreprocessingError` — Document preprocessing failed

**Exception:** `lexigram.ai.rag.exceptions.PreprocessingError`

**Cause:** A document couldn't be loaded, parsed, or chunked — unsupported format, corrupt file, or encoding issue.

**Fix:**
- Confirm the document format is in `IngestionConfig.document_formats`.
- For PDFs, install `lexigram-ai-rag[pdf]`.
- For web pages, install `lexigram-ai-rag[web]`.

## RAG pipeline returns empty results

**Cause:** The vector store has no documents indexed, or the `similarity_threshold` is too high.

**Fix:**
- Verify documents were ingested (check collection vector count).
- Lower `similarity_threshold` in `RAGConfig`.
- Check `top_k` is set appropriately.

## FlashRank / LLMLingua-2 not available

**Cause:** Optional dependencies are not installed.

**Fix:**
```bash
uv add "lexigram-ai-rag[compression,reranking]"
```

The provider logs `llmlingua2_compressor_skipped_not_installed` and
`flashrank_reranker_skipped_not_installed` at debug level when extras
are missing — no error is raised.

## Hallucination detection false positives

**Cause:** `min_faithfulness` or `min_relevance` thresholds are too strict for your domain.

**Fix:**
```python
from lexigram.ai.rag.config import QualityAssuranceConfig

pipeline_cfg = PipelineConfig(
    quality_assurance=QualityAssuranceConfig(
        min_faithfulness=0.6,  # Default 0.7
        min_relevance=0.5,     # Default 0.6
        warn_low_quality=True, # Log warnings instead of rejecting
    ),
)
```

## ChunkingError: Document cannot be split

```python
ChunkingError: Chunking failed for document 'report.pdf': token count 0 after chunking
```

**Cause:** The document content could not be split into chunks — either the text is empty after parsing, or the chunking strategy (`RecursiveCharacterTextSplitter`, `TokenTextSplitter`) failed to produce any segments.

**Fix:** Verify the document was parsed correctly:

```python
from lexigram.ai.rag.loaders.core import AbstractDocumentLoader

loader = AbstractDocumentLoader()
text = await loader.load("report.pdf")
print(f"Extracted text length: {len(text)}")  # should be > 0
```

If the format is unsupported, install the required extra:

```bash
uv add "lexigram-ai-rag[pdf]"
```

## Multimodal loader fails for media files

```python
AudioLoaderError: Failed to load audio file 'meeting.wav': Unsupported codec
VideoLoaderError: Failed to load video file 'demo.mp4': FFmpeg not found
ImageLoaderError: Failed to load image 'scan.png': Unsupported format
```

**Cause:** The multimodal loader requires FFmpeg (for audio/video) or PIL/Pillow (for images). Audio/video codec support depends on the system FFmpeg installation.

**Fix:** Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Verify FFmpeg is available
ffmpeg -version
```

For images, ensure Pillow is installed:

```bash
uv add Pillow
```

## Hybrid search returns no results

**Symptom:** `use_hybrid_search: true` but queries return zero results, while `use_hybrid_search: false` works.

**Cause:** The vector store backend does not support hybrid search (semantic + keyword), or the keyword index has not been built for the collection.

**Fix:** Verify the backend supports hybrid search. For pgvector, ensure a full-text search (GIN) index exists on the document text column:

```sql
CREATE INDEX IF NOT EXISTS idx_docs_fts ON documents USING GIN(to_tsvector('english', content));
```

Or disable hybrid search if your backend lacks keyword indexing:

```yaml
ai_rag:
  use_hybrid_search: false
```

## Synthesis fails with token limit exceeded

```python
SynthesisError: Answer synthesis failed — context window exceeded
```

**Cause:** The retrieved documents are too large when combined, exceeding the LLM model's context window.

**Fix:** Reduce the amount of context sent to the synthesizer:

```yaml
ai_rag:
  top_k: 3               # retrieve fewer documents
  similarity_threshold: 0.8  # only highly relevant chunks
  synthesis:
    max_context_tokens: 4096  # truncate context
```

Or use a model with a larger context window (e.g. `gpt-4-turbo` instead of `gpt-3.5-turbo`).
