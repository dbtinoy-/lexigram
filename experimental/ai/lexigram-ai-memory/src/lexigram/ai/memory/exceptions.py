"""Exceptions for lexigram-ai-memory."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIMemoryError as _ContractsAIMemoryError
from lexigram.contracts.ai.memory import ConsolidationError


class MemorySystemError(_ContractsAIMemoryError):
    """Base exception for memory operations."""

    _code: str = "LEX_ERR_MEM_005"


class MemoryStoreError(MemorySystemError):
    """Raised when a backend store operation fails."""

    _code: str = "LEX_ERR_MEM_006"

    def __init__(self, message: str, store: str | None = None) -> None:
        """Initialise with optional store name context.

        Args:
            message: Human-readable description.
            store: Name of the store that raised the error.
        """
        super().__init__(message)
        self.store = store


class MemoryCapacityError(MemorySystemError):
    """Raised when a memory store is at capacity and cannot accept new entries."""

    _code: str = "LEX_ERR_MEM_008"

    def __init__(self, message: str, capacity: int | None = None) -> None:
        """Initialise with optional capacity context.

        Args:
            message: Human-readable description.
            capacity: Maximum capacity that was exceeded.
        """
        super().__init__(message)
        self.capacity = capacity


class EmbeddingError(MemorySystemError):
    """Raised when generating or storing an embedding fails."""

    _code: str = "LEX_ERR_MEM_009"


class FactExtractionError(MemorySystemError):
    """Raised when entity/fact extraction from text fails."""

    _code: str = "LEX_ERR_MEM_010"


__all__ = [
    "ConsolidationError",
    "EmbeddingError",
    "FactExtractionError",
    "MemoryCapacityError",
    "MemoryStoreError",
    "MemorySystemError",
]
