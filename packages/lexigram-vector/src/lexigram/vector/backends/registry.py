"""Vector store registry — registry-based dispatch of vector backends."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.vector.constants import (
    BACKEND_MEMORY,
    BACKEND_PGVECTOR,
    BACKEND_PINECONE,
    BACKEND_QDRANT,
)

VectorStoreBuilder = Callable[[Any], Any]


class VectorStoreRegistry:
    """Registry of vector-store builders, keyed by backend name.

    A backend name maps to a builder that constructs the corresponding
    vector store from a :class:`~lexigram.vector.config.VectorConfig`.
    The pgvector backend returns ``None`` because it requires a
    ``DatabaseProviderProtocol`` that can only be resolved from the DI
    container during :meth:`boot`.

    Usage::

        registry = VectorStoreRegistry.with_defaults()
        store = registry.create_store("memory", config)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, VectorStoreBuilder] = {}

    @classmethod
    def with_defaults(cls) -> VectorStoreRegistry:
        """Return a registry populated with the built-in vector backends.

        Returns:
            A :class:`VectorStoreRegistry` pre-registered for memory,
            pinecone, qdrant, and pgvector.
        """
        registry = cls()

        def _memory(config: Any) -> Any:
            from lexigram.vector.backends.memory import MemoryVectorStore

            return MemoryVectorStore(config=config.memory)

        def _pinecone(config: Any) -> Any:
            from lexigram.vector.backends.pinecone import PineconeStore

            return PineconeStore(config=config.pinecone)

        def _qdrant(config: Any) -> Any:
            from lexigram.vector.backends.qdrant import QdrantStore

            return QdrantStore(config=config.qdrant)

        def _pgvector(_config: Any) -> Any:
            # Cannot instantiate without a DB provider — sentinel, resolved in boot().
            return None

        registry.register(BACKEND_MEMORY, _memory)
        registry.register(BACKEND_PINECONE, _pinecone)
        registry.register(BACKEND_QDRANT, _qdrant)
        registry.register(BACKEND_PGVECTOR, _pgvector)
        return registry

    def register(self, backend: str, builder: VectorStoreBuilder) -> None:
        """Register a builder under a backend name.

        Args:
            backend: Backend name (e.g. ``"memory"``).
            builder: Callable ``(VectorConfig) -> VectorStoreProtocol | None``.
        """
        self._builders[backend] = builder

    def create_store(self, backend: str, config: Any) -> Any:
        """Build a vector store for a backend name.

        Args:
            backend: Backend name to dispatch on.
            config: VectorConfig used to construct the backend.

        Returns:
            An instantiated vector store, or ``None`` for pgvector (sentinel
            resolved during boot).

        Raises:
            ValueError: If *backend* is not a registered backend.
        """
        builder = self._builders.get(backend)
        if builder is None:
            msg = f"Unknown vector backend: {backend}"
            raise ValueError(msg)
        return builder(config)

    def backends(self) -> list[str]:
        """Return the registered backend names.

        Returns:
            List of backend names in registration order.
        """
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["VectorStoreBuilder", "VectorStoreRegistry"]
