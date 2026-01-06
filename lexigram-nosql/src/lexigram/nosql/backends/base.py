"""Abstract base class for document store backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from lexigram.contracts.core.health import HealthCheckResult
    from lexigram.contracts.data.nosql.nosql import CollectionProtocol

logger = get_logger(__name__)


class AbstractDocumentStore(ABC):
    """Base implementation for document store backends.

    Subclasses implement backend-specific connection and collection
    logic.  This class provides lifecycle management, health check
    plumbing, and the common collection cache.

    Implements: ``DocumentStoreProtocol``
    """

    def __init__(self, *, database_name: str, **kwargs: Any) -> None:
        self._database_name = database_name
        self._connected = False
        self._collections: dict[str, CollectionProtocol] = {}

    @property
    def database_name(self) -> str:
        """The database / keyspace name."""
        return self._database_name

    def is_connected(self) -> bool:
        """Check if the store is currently connected."""
        return self._connected

    def collection(self, name: str) -> CollectionProtocol:
        """Get or create a cached collection handle.

        Args:
            name: Collection name.

        Returns:
            A backend-specific ``CollectionProtocol`` implementation.

        Raises:
            RuntimeError: If the store is not connected.
        """
        if name not in self._collections:
            self._collections[name] = self._create_collection(name)
        return self._collections[name]

    @abstractmethod
    def _create_collection(self, name: str) -> CollectionProtocol:
        """Create a backend-specific collection handle."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the document store."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close all connections."""
        ...

    @abstractmethod
    def session(self) -> AbstractAsyncContextManager:
        """Create a session context for multi-document transactions."""
        ...

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """List all collection names in the database."""
        ...

    @abstractmethod
    async def drop_collection(self, name: str) -> None:
        """Drop a collection by name."""
        ...

    @abstractmethod
    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check document store connectivity and health."""
        ...


__all__ = ["AbstractDocumentStore"]
