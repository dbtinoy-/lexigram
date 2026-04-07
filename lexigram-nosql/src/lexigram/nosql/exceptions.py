"""NoSQL-specific exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import LexigramError


class NoSQLError(LexigramError):
    """Base exception for all NoSQL operations."""

    _code: str = "LEX_ERR_NOSQL_001"


class NoSQLConnectionError(NoSQLError):
    """Failed to connect to the document store."""

    _code: str = "LEX_ERR_NOSQL_002"


class DocumentNotFoundError(NoSQLError):
    """Requested document does not exist."""

    _code: str = "LEX_ERR_NOSQL_003"


class DuplicateKeyError(NoSQLError):
    """Insert/update violated a unique constraint."""

    _code: str = "LEX_ERR_NOSQL_004"


class DocumentValidationError(NoSQLError):
    """Document failed schema validation."""

    _code: str = "LEX_ERR_NOSQL_005"


class TransactionError(NoSQLError):
    """Multi-document transaction failed."""

    _code: str = "LEX_ERR_NOSQL_006"


__all__ = [
    "DocumentNotFoundError",
    "DocumentValidationError",
    "DuplicateKeyError",
    "NoSQLConnectionError",
    "NoSQLError",
    "TransactionError",
]
