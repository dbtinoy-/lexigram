"""Search Query Building and Validation"""

from __future__ import annotations

from lexigram.search.query.builder import SearchQueryBuilder
from lexigram.search.query.safe_query import (
    AlgoliaBackend,
    ElasticsearchBackend,
    QueryBackend,
    SafeQueryBuilder,
    create_algolia_builder,
    create_elasticsearch_builder,
)
from lexigram.search.query.suggestions import (
    Suggestion,
    SuggestionEngine,
    SuggestionResult,
)
from lexigram.search.query.types import (
    AggregationSpec,
    FilterCondition,
    QueryOperator,
    SafeSearchQuery,
    SortDirection,
    SortField,
)

__all__ = [
    "AggregationSpec",
    "AlgoliaBackend",
    "ElasticsearchBackend",
    "FilterCondition",
    "QueryBackend",
    "QueryOperator",
    "SafeQueryBuilder",
    "SafeSearchQuery",
    "SearchQueryBuilder",
    "SortDirection",
    "SortField",
    "Suggestion",
    "SuggestionEngine",
    "SuggestionResult",
]
