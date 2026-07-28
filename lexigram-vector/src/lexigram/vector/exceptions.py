"""Vector store exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import InfrastructureError


class VectorError(InfrastructureError):
    """Base exception for all vector store operations."""

    _code: str = "LEX_ERR_VEC_005"


class VectorConnectionError(VectorError):
    """Failed to connect to the vector store."""

    _code: str = "LEX_ERR_VEC_006"


class CollectionNotFoundError(VectorError):
    """Requested collection does not exist."""

    _code: str = "LEX_ERR_VEC_007"

    def __init__(self, collection_name: str) -> None:
        """Initialize with the missing collection name."""
        self.collection_name = collection_name
        super().__init__(
            f"Collection '{collection_name}' not found",
        )


class CollectionAlreadyExistsError(VectorError):
    """Attempted to create a collection that already exists."""

    _code: str = "LEX_ERR_VEC_008"

    def __init__(self, collection_name: str) -> None:
        """Initialize with the conflicting collection name."""
        self.collection_name = collection_name
        super().__init__(
            f"Collection '{collection_name}' already exists",
        )


class DimensionMismatchError(VectorError):
    """Vector dimensionality does not match the collection."""

    _code: str = "LEX_ERR_VEC_009"

    def __init__(
        self,
        expected: int,
        actual: int,
        record_id: str | None = None,
    ) -> None:
        """Initialize with expected and actual dimensions."""
        self.expected = expected
        self.actual = actual
        self.record_id = record_id
        msg = f"Expected dimension {expected}, got {actual}"
        if record_id:
            msg += f" (record '{record_id}')"
        super().__init__(msg)


class VectorConfigError(VectorError):
    """Invalid vector store configuration."""

    _code: str = "LEX_ERR_VEC_010"


class FilterCompilationError(VectorError):
    """Failed to compile a metadata filter for the target backend."""

    _code: str = "LEX_ERR_VEC_011"

    def __init__(self, message: str, backend: str) -> None:
        """Initialize with error details and backend name."""
        self.backend = backend
        super().__init__(
            f"[{backend}] Filter compilation failed: {message}",
        )


class VectorUpsertError(VectorError):
    """Failed to upsert vectors."""

    _code: str = "LEX_ERR_VEC_012"


class VectorSearchError(VectorError):
    """Failed to execute similarity search."""

    _code: str = "LEX_ERR_VEC_013"


class VectorDeleteError(VectorError):
    """Failed to delete vectors."""

    _code: str = "LEX_ERR_VEC_014"


class VectorTimeoutError(VectorError):
    """Vector store operation timed out."""

    _code: str = "LEX_ERR_VEC_015"
