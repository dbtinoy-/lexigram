"""Tests for corpus ingestion into the in-memory vector store."""

from __future__ import annotations

from pathlib import Path

from lexigram.contracts.data.vector.types import SearchQuery
from lexigram.vector.backends.memory import MemoryVectorStore

from rag_docs.di.provider import resolve_default_docs_dir
from rag_docs.repository.embedder import EMBEDDING_DIMENSION, HashingEmbedder
from rag_docs.repository.index_builder import (
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
    results = await collection.search(SearchQuery(vector=[0.0] * EMBEDDING_DIMENSION, top_k=5))
    assert results == []


async def test_title_falls_back_to_file_name_without_heading(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "untitled-notes.md").write_text(
        "No heading here at all, just body prose for the embedder.\n"
    )

    _, collection, _ = await build_docs_store(docs, HashingEmbedder())

    record = await collection.get(["untitled-notes.md#0"])
    assert record
    assert record[0].metadata["title"] == "Untitled Notes"


async def test_default_docs_dir_points_at_repo_docs() -> None:
    """resolve_default_docs_dir() is CWD-proof — anchored to this file's location."""
    default_dir = resolve_default_docs_dir()

    assert default_dir.name == "docs"
    assert default_dir.exists()
