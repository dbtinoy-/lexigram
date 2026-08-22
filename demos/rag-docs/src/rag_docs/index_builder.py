"""Corpus ingestion: walk markdown, chunk, embed, upsert."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexigram.ai.rag.loaders.core import MarkdownLoader
from lexigram.contracts.data.vector.types import CollectionConfig, VectorRecord
from lexigram.vector.backends.memory import MemoryVectorCollection, MemoryVectorStore
from rag_docs.embedder import EMBEDDING_DIMENSION, HashingEmbedder

CORPUS_COLLECTION_NAME = "lexigram_docs"


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
        CollectionConfig(name=CORPUS_COLLECTION_NAME, dimension=EMBEDDING_DIMENSION)
    )
    collection = await store.get_collection(CORPUS_COLLECTION_NAME)

    loader = MarkdownLoader()
    files = sorted(docs_dir.rglob("*.md"))
    loaded: list[tuple[str, list]] = []
    for path in files:
        relative = path.relative_to(docs_dir).as_posix()
        loaded.append((relative, await loader.load(path)))

    # Fit IDF over the whole corpus before embedding so rare, distinctive
    # tokens outweigh ubiquitous ones at query time too (same instance).
    embedder.fit([chunk.text for _, chunks in loaded for chunk in chunks])

    records: list[VectorRecord] = []
    for relative, chunks in loaded:
        # Batch the file's chunks into one embed call (O(files) calls total).
        vectors = await embedder.embed([chunk.text for chunk in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            title = _extract_title(
                chunk.text, Path(relative).stem.replace("-", " ").title()
            )
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
