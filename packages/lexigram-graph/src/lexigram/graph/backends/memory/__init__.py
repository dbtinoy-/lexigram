"""In-memory graph backend."""

from __future__ import annotations

from lexigram.graph.backends.memory.backend import InMemoryGraphStore
from lexigram.graph.backends.memory.graph import InMemoryGraph

__all__ = ["InMemoryGraph", "InMemoryGraphStore"]
