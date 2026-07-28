"""Lexigram Search Package."""

from __future__ import annotations

import importlib.metadata

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

from lexigram.search.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.search.analytics import (
        InMemorySearchAnalyticsRecorder,
        SearchAnalyticsRecorder,
    )
    from lexigram.search.config import (
        BackendType,
        IndexConfig,
        NamedSearchConfig,
        SearchConfig,
    )
    from lexigram.search.di.provider import SearchProvider
    from lexigram.search.engine import (
        FederatedResults,
        FederatedSearchEngine,
        SearchableModel,
        SearchEngine,
    )
    from lexigram.search.exceptions import (
        BackendError,
        ConfigurationError,
        QueryError,
        SearchError,
        SearchIndexError,
    )
    from lexigram.search.filterset import (
        FilterCondition,
        FilterOperator,
        FilterSet,
        FilterSetTranslator,
    )
    from lexigram.search.query import (
        Suggestion,
        SuggestionEngine,
        SuggestionResult,
    )
    from lexigram.search.repository import SearchEntityRepository
    from lexigram.search.types import (
        RAGSearchResult,
        SearchQuery,
        SearchResponse,
        SearchStrategy,
    )
    from lexigram.search.validation import (
        SearchQueryValidator,
        sanitize_search_filters,
        sanitize_search_query,
        validate_index_name,
        validate_search_filters,
        validate_search_query,
        validate_search_sort,
    )

_LAZY_IMPORTS = {
    # FilterSet translator
    "FilterCondition": "lexigram.search.filterset",
    "FilterOperator": "lexigram.search.filterset",
    "FilterSet": "lexigram.search.filterset",
    "FilterSetTranslator": "lexigram.search.filterset",
    # Module
    "SearchModule": "lexigram.search.module",
    "BackendType": "lexigram.search.config",
    "NamedSearchConfig": "lexigram.search.config",
    "SearchConfig": "lexigram.search.config",
    "SearchableModel": "lexigram.search.engine",
    "SearchEngine": "lexigram.search.engine",
    "FederatedSearchEngine": "lexigram.search.engine",
    "FederatedResults": "lexigram.search.engine",
    "BackendError": "lexigram.search.exceptions",
    "ConfigurationError": "lexigram.search.exceptions",
    "QueryError": "lexigram.search.exceptions",
    "SearchError": "lexigram.search.exceptions",
    "SearchIndexError": "lexigram.search.exceptions",
    "SearchProvider": "lexigram.search.di.provider",
    "SearchEntityRepository": "lexigram.search.repository",
    "IndexConfig": "lexigram.search.config",
    "RAGSearchResult": "lexigram.search.types",
    "SearchQuery": "lexigram.search.types",
    "SearchResponse": "lexigram.search.types",
    "SearchResult": "lexigram.search.types",
    "SearchStrategy": "lexigram.search.types",
    "SearchQueryValidator": "lexigram.search.validation",
    "sanitize_search_filters": "lexigram.search.validation",
    "sanitize_search_query": "lexigram.search.validation",
    "validate_index_name": "lexigram.search.validation",
    "validate_search_filters": "lexigram.search.validation",
    "validate_search_query": "lexigram.search.validation",
    "validate_search_sort": "lexigram.search.validation",
    "InMemorySearchAnalyticsRecorder": "lexigram.search.analytics",
    "SearchAnalyticsRecorder": "lexigram.search.analytics",
    "Suggestion": "lexigram.search.query",
    "SuggestionEngine": "lexigram.search.query",
    "SuggestionResult": "lexigram.search.query",
    # Events
    "IndexingCompletedEvent": "lexigram.search.events",
    "SearchExecutedEvent": "lexigram.search.events",
    # Hooks
    "SearchIndexedHook": "lexigram.search.hooks",
    "SearchQueryExecutedHook": "lexigram.search.hooks",
}


def __getattr__(name: str) -> Any:
    if name == "__version__":
        return __version__
    if name in _LAZY_IMPORTS:
        import importlib

        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [*list(_LAZY_IMPORTS.keys()), "__version__"]
