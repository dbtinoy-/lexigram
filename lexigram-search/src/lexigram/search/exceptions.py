"""Search exceptions - consolidated to base framework exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import (
    DomainError,
    InfrastructureError,
    LexigramError,
)


class SearchError(LexigramError):
    """Base exception for search operations."""

    _code: str = "LEX_ERR_SEARCH_001"


class IndexNotFoundError(DomainError):
    """Raised when index is not found."""

    _code: str = "LEX_ERR_SEARCH_002"


class BackendError(InfrastructureError):
    """Raised when search backend encounters an error."""

    _code: str = "LEX_ERR_SEARCH_003"


class SearchValidationError(SearchError):
    """Raised when search query validation fails."""

    _code: str = "LEX_ERR_SEARCH_004"


class TransformationError(SearchError):
    """Raised when document transformation fails."""

    _code: str = "LEX_ERR_SEARCH_005"


class CacheError(SearchError):
    """Raised when search cache operation fails."""

    _code: str = "LEX_ERR_SEARCH_006"


class QueryError(SearchError):
    """Raised when search query execution fails."""

    _code: str = "LEX_ERR_SEARCH_007"


class ConfigurationError(SearchError):
    """Raised when search configuration is invalid."""

    _code: str = "LEX_ERR_SEARCH_008"


class SearchIndexError(SearchError):
    """Raised when search index operation fails."""

    _code: str = "LEX_ERR_SEARCH_009"


class SchedulerError(SearchError):
    """Raised when search scheduler operation fails."""

    _code: str = "LEX_ERR_SEARCH_010"


__all__ = [
    "BackendError",
    "CacheError",
    "ConfigurationError",
    "IndexNotFoundError",
    "QueryError",
    "SchedulerError",
    "SearchError",
    "SearchIndexError",
    "SearchValidationError",
    "TransformationError",
]
