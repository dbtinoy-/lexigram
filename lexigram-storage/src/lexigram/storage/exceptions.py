"""Storage exceptions - consolidated to base framework exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import DomainError, LexigramError


class StorageError(LexigramError):
    """Base exception for storage errors."""

    _code: str = "LEX_ERR_STORE_001"


class StorageFileNotFoundError(DomainError):
    """Raised when file is not found."""

    _code: str = "LEX_ERR_STORE_002"


class StorageUnsupportedOperationError(StorageError):
    """Raised when the requested operation is not supported by the storage driver."""

    _code: str = "LEX_ERR_STORE_003"


class TransactionError(StorageError):
    """Raised when a transaction operation fails."""

    _code: str = "LEX_ERR_STORE_004"


class QuotaExceededError(StorageError):
    """Raised when a storage quota or size limit is exceeded."""

    _code: str = "LEX_ERR_STORE_005"


class InvalidPathError(StorageError):
    """Raised when a path is invalid or attempts directory traversal."""

    _code: str = "LEX_ERR_STORE_006"


class StorageUnavailableError(StorageError):
    """Raised when the storage backend is not reachable or unavailable."""

    _code: str = "LEX_ERR_STORE_007"


class ChecksumMismatchError(StorageError):
    """Raised when a file's checksum does not match the expected value."""

    _code: str = "LEX_ERR_STORE_008"


__all__ = [
    "ChecksumMismatchError",
    "InvalidPathError",
    "QuotaExceededError",
    "StorageError",
    "StorageFileNotFoundError",
    "StorageUnavailableError",
    "StorageUnsupportedOperationError",
    "TransactionError",
]
