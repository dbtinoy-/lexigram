"""Search Engine Abstractions & Validation."""

from __future__ import annotations

from lexigram.search.config import SearchConfig
from lexigram.search.engine.base import SearchEngine
from lexigram.search.engine.engine import (
    BulkOperationResult,
    BulkResult,
    DefaultSearchEngine,
    SearchQuery,
)
from lexigram.search.engine.federation import (
    FederatedResults,
    FederatedSearchEngine,
    FederatedSearchResult,
)
from lexigram.search.engine.models import SearchableModel
from lexigram.search.engine.validation import MAX_QUERY_LENGTH, validate_search_query
from lexigram.search.types import SearchResponse

__all__ = [
    "MAX_QUERY_LENGTH",
    "BulkOperationResult",
    "BulkResult",
    "DefaultSearchEngine",
    "FederatedResults",
    "FederatedSearchEngine",
    "FederatedSearchResult",
    "SearchConfig",
    "SearchEngine",
    "SearchQuery",
    "SearchResponse",
    "SearchableModel",
    "validate_search_query",
]
