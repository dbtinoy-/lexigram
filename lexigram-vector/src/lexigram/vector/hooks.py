"""Root hook payload surface for lexigram-vector.

Defines canonical payload dataclasses for vector store lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "VectorIndexedHook",
    "VectorSearchedHook",
]


@dataclass(frozen=True, kw_only=True)
class VectorIndexedHook:
    """Payload fired when a vector embedding is written to the store.

    Attributes:
        collection: Name of the vector collection that was written to.
        document_id: Identifier of the document whose embedding was stored.
    """

    collection: str
    document_id: str


@dataclass(frozen=True, kw_only=True)
class VectorSearchedHook:
    """Payload fired after a vector similarity search completes.

    Attributes:
        collection: Name of the vector collection that was searched.
        result_count: Number of nearest-neighbour results returned.
    """

    collection: str
    result_count: int
