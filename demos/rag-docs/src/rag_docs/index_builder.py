"""Corpus ingestion: walk markdown, chunk, embed, upsert."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexigram.ai.rag.loaders.core import MarkdownLoader
from lexigram.contracts.data.vector.types import CollectionConfig, VectorRecord
from lexigram.vector.backends.memory import MemoryVectorCollection, MemoryVectorStore
from rag_docs.embedder import HashingEmbedder

CORPUS_COLLECTION_NAME = "lexigram_docs"
_EMBEDDING_DIMENSION = 256


@dataclass(frozen=True)
class IndexStats:
    """Corpus statistics from an index build.

    Attributes:
        files: Markdown files ingested.
        chunks: Vector records upserted.
    """

    files: int
    chunks: int


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


async def build_docs_store(
    docs_dir: Path,
    embedder: HashingEmbedder,
) -> tuple[MemoryVectorStore, MemoryVectorCollection, IndexStats]:
    """Walk ``docs_dir`` for markdown and populate the vector collection.

    Args:
        docs_dir: Directory scanned recursively for ``*.md`` files.
        embedder: The deterministic embedder used for chunks.

    Returns:
        The connected store, the ready collection, and corpus stats.
    """
    store = MemoryVectorStore()
    await store.connect()
    await store.create_collection(
        CollectionConfig(name=CORPUS_COLLECTION_NAME, dimension=_EMBEDDING_DIMENSION)
    )
    collection = await store.get_collection(CORPUS_COLLECTION_NAME)

    loader = MarkdownLoader()
    files = sorted(docs_dir.rglob("*.md"))
    records: list[VectorRecord] = []
    for path in files:
        relative = path.relative_to(docs_dir).as_posix()
        chunks = await loader.load(path)
        for chunk in chunks:
            title = _extract_title(chunk.text, path.stem.replace("-", " ").title())
            vector = (await embedder.embed([chunk.text]))[0]
            records.append(
                VectorRecord(
                    id=f"{relative}#{chunk.chunk_index}",
                    vector=vector,
                    metadata={
                        "source": relative,
                        "chunk_index": chunk.chunk_index,
                        "title": title,
                    },
                    content=chunk.text,
                )
            )

    if records:
        await collection.upsert(records)
    return store, collection, IndexStats(files=len(files), chunks=len(records))


__all__ = ["CORPUS_COLLECTION_NAME", "IndexStats", "build_docs_store"]
