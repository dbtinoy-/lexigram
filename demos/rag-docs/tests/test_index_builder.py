"""Tests for corpus ingestion into the in-memory vector store."""

from __future__ import annotations

from pathlib import Path

from lexigram.contracts.data.vector.types import SearchQuery
from lexigram.vector.backends.memory import MemoryVectorStore

from rag_docs.embedder import HashingEmbedder
from rag_docs.index_builder import (
    CORPUS_COLLECTION_NAME,
    IndexStats,
    build_docs_store,
)


def make_corpus(root: Path) -> Path:
    docs = root / "docs"
    (docs / "guide").mkdir(parents=True)
    (docs / "README.md").write_text(
        "# Overview\n\nModules export services through provider wiring.\n"
        "Second sentence adds body text for chunking.\n"
    )
    (docs / "guide" / "advanced.md").write_text(
        "# Advanced\n\nThe registry maps names to strategies.\n"
    )
    return docs


async def test_build_indexes_all_markdown_files(tmp_path: Path) -> None:
    docs = make_corpus(tmp_path)

    store, collection, stats = await build_docs_store(docs, HashingEmbedder())

    assert isinstance(store, MemoryVectorStore)
    assert stats.files == 2
    assert stats.chunks >= 2
    assert collection is not None


async def test_record_identity_and_metadata(tmp_path: Path) -> None:
    docs = make_corpus(tmp_path)

    _, collection, _ = await build_docs_store(docs, HashingEmbedder())

    readme = await collection.get(["README.md#0"])
    assert readme
    assert readme[0].metadata["source"] == "README.md"
    assert readme[0].metadata["chunk_index"] == 0
    assert readme[0].metadata["title"] == "Overview"
    nested = await collection.get(["guide/advanced.md#0"])
    assert nested
    assert nested[0].metadata["title"] == "Advanced"


async def test_empty_corpus_is_valid(tmp_path: Path) -> None:
    docs = tmp_path / "empty-docs"
    docs.mkdir()

    _, collection, stats = await build_docs_store(docs, HashingEmbedder())

    assert stats == IndexStats(files=0, chunks=0)
    results = await collection.search(SearchQuery(vector=[0.0] * 256, top_k=5))
    assert results == []
