"""Document-centric adapters bridging embedding + vector storage."""

from __future__ import annotations

from lexigram.vector.adapters.document_store import DocumentVectorStoreAdapter
from lexigram.vector.adapters.vector_store import VectorStoreAdapter

__all__ = [
    "DocumentVectorStoreAdapter",
    "VectorStoreAdapter",
]
