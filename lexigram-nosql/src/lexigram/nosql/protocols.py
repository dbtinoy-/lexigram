"""Public protocol surface for ``lexigram.nosql``."""

from __future__ import annotations

from lexigram.contracts.data.graph.protocols import GraphProtocol, GraphStoreProtocol
from lexigram.contracts.data.nosql.nosql import (
    CollectionProtocol,
    DocumentStoreProtocol,
)

__all__ = [
    "CollectionProtocol",
    "DocumentStoreProtocol",
    "GraphProtocol",
    "GraphStoreProtocol",
]
