"""Safe query builder with injection protection.

**MANDATORY ENTRY POINT** for all user-facing search queries.

All user-supplied input MUST be routed through :class:`SafeQueryBuilder`
before reaching any search backend.  Backend-specific translators
(:class:`ElasticsearchBackend`, :class:`AlgoliaBackend`, etc.) only ever
receive :class:`~lexigram.search.query.types.SafeSearchQuery` objects that
have already been validated and field-name-sanitized by this builder.

Direct instantiation of backend query dicts from raw user input is
prohibited — it bypasses injection protection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import Any, Literal

from lexigram.logging import get_logger
from lexigram.search.query.types import SafeSearchQuery

logger = get_logger(__name__)


class QueryBackend(ABC):
    """Abstract search backend for query building."""

    @abstractmethod
    def escape(self, value: str) -> str:
        """Escape special characters for backend.

        Args:
            value: Value to escape

        Returns:
            Escaped value
        """
        ...

    @abstractmethod
    def build(self, query: SafeSearchQuery) -> dict[str, Any]:
        """Build backend-specific query.

        Args:
            query: Structured query

        Returns:
            Backend query dict
        """
        ...


class ElasticsearchBackend(QueryBackend):
    """Elasticsearch query backend."""

    # Special characters that need escaping in Elasticsearch
    SPECIAL_CHARS = r'+-=&|><!(){}[]^"~*?:\/'

    def escape(self, value: str) -> str:
        """Escape Elasticsearch special characters.

        Args:
            value: Value to escape

        Returns:
            Escaped value
        """
        # Escape special characters with backslash
        return re.sub(r'([+\-=&|><!(){}[\]^"~*?:\\/])', r"\\\1", value)

    def build(self, query: SafeSearchQuery) -> dict[str, Any]:
        """Build Elasticsearch query DSL.

        Args:
            query: Structured query

        Returns:
            Elasticsearch query dict
        """
        query.validate()

        if query.query_type == "match":
            return {
                "match": {
                    query.field: {
                        "query": self.escape(str(query.value)),
                        "operator": "and",
                    },
                },
            }

        if query.query_type == "term":
            return {"term": {query.field: self.escape(str(query.value))}}

        if query.query_type == "range":
            # Range queries don't need escaping
            return {"range": {query.field: query.value}}

        if query.query_type == "bool":
            # Build boolean query
            if not query.operator or not query.children:
                raise ValueError("bool query requires operator and children")
            bool_clause = query.operator.lower()  # and -> must, or -> should
            clause_map = {"and": "must", "or": "should", "not": "must_not"}

            return {
                "bool": {
                    clause_map[bool_clause]: [
                        self.build(child) for child in query.children
                    ],
                },
            }

        raise ValueError(f"Unsupported query type: {query.query_type}")


class AlgoliaBackend(QueryBackend):
    """Algolia query backend."""

    def escape(self, value: str) -> str:
        """Escape Algolia special characters.

        Args:
            value: Value to escape

        Returns:
            Escaped value
        """
        # Algolia uses quotes for exact matching
        # Escape quotes and backslashes
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def build(self, query: SafeSearchQuery) -> dict[str, Any]:
        """Build Algolia query parameters.

        Args:
            query: Structured query

        Returns:
            Algolia query dict
        """
        query.validate()

        if query.query_type == "match":
            # Algolia uses simple query string
            return {
                "query": self.escape(str(query.value)),
                "restrictSearchableAttributes": [query.field],
            }

        if query.query_type == "term":
            # Exact match using quotes
            return {
                "query": f'"{self.escape(str(query.value))}"',
                "restrictSearchableAttributes": [query.field],
            }

        if query.query_type == "range":
            # Algolia uses filters for ranges
            filters = []
            if "gte" in query.value:
                filters.append(f"{query.field} >= {query.value['gte']}")
            if "lte" in query.value:
                filters.append(f"{query.field} <= {query.value['lte']}")

            return {"filters": " AND ".join(filters)}

        if query.query_type == "bool":
            # Combine child queries
            if not query.operator or not query.children:
                raise ValueError("bool query requires operator and children")
            operator = " AND " if query.operator == "AND" else " OR "

            # Build filter strings
            child_results = list(map(self.build, query.children))

            # Combine filters
            all_filters = []
            for result in child_results:
                if "filters" in result:
                    all_filters.append(f"({result['filters']})")

            if all_filters:
                return {"filters": operator.join(all_filters)}

            # Fallback to query combination
            return {"query": operator.join(r.get("query", "") for r in child_results)}

        raise ValueError(f"Unsupported query type: {query.query_type}")


class SafeQueryBuilder:
    """Safe query builder preventing injection attacks.

    Uses structured queries instead of string concatenation.
    """

    def __init__(self, backend: QueryBackend) -> None:
        """Initialize query builder.

        Args:
            backend: Search backend (Elasticsearch, Algolia, etc.)
        """
        self.backend = backend

    def match(self, field: str, value: str) -> SafeSearchQuery:
        """Create match query (full-text search).

        Args:
            field: Field to search
            value: Search value (will be escaped)

        Returns:
            Match query
        """
        self._validate_field_name(field)

        return SafeSearchQuery(
            query_type="match",
            field=field,
            value=value,
        )

    def term(self, field: str, value: str) -> SafeSearchQuery:
        """Create term query (exact match).

        Args:
            field: Field to match
            value: Exact value (will be escaped)

        Returns:
            Term query
        """
        self._validate_field_name(field)

        return SafeSearchQuery(
            query_type="term",
            field=field,
            value=value,
        )

    def range(
        self,
        field: str,
        gte: Any | None = None,
        lte: Any | None = None,
        gt: Any | None = None,
        lt: Any | None = None,
    ) -> SafeSearchQuery:
        """Create range query.

        Args:
            field: Field to range search
            gte: Greater than or equal
            lte: Less than or equal
            gt: Greater than
            lt: Less than

        Returns:
            Range query
        """
        self._validate_field_name(field)

        value = {}
        if gte is not None:
            value["gte"] = gte
        if lte is not None:
            value["lte"] = lte
        if gt is not None:
            value["gt"] = gt
        if lt is not None:
            value["lt"] = lt

        if not value:
            raise ValueError("Range query requires at least one bound")

        return SafeSearchQuery(
            query_type="range",
            field=field,
            value=value,
        )

    def bool(
        self,
        operator: Literal["AND", "OR", "NOT"],
        *queries: SafeSearchQuery,
    ) -> SafeSearchQuery:
        """Create boolean query combining multiple queries.

        Args:
            operator: Boolean operator (AND, OR, NOT)
            *queries: Child queries to combine

        Returns:
            Boolean query
        """
        if not queries:
            raise ValueError("Boolean query requires at least one child")

        return SafeSearchQuery(
            query_type="bool",
            operator=operator,
            children=list(queries),
        )

    def build(self, query: SafeSearchQuery) -> dict[str, Any]:
        """Build backend-specific query.

        Args:
            query: Structured query

        Returns:
            Backend query dict
        """
        return self.backend.build(query)

    def _validate_field_name(self, field: str) -> None:
        """Validate field name is safe.

        Args:
            field: Field name to validate

        Raises:
            ValueError: If field name invalid
        """
        # Only allow alphanumeric, underscore, dash, dot
        if not re.match(r"^[a-zA-Z0-9._-]+$", field):
            raise ValueError(
                f"Invalid field name: {field}. "
                f"Only alphanumeric, underscore, dash, and dot allowed.",
            )


# Convenience functions
def create_elasticsearch_builder() -> SafeQueryBuilder:
    """Create query builder for Elasticsearch.

    Returns:
        Configured query builder
    """
    return SafeQueryBuilder(ElasticsearchBackend())


def create_algolia_builder() -> SafeQueryBuilder:
    """Create query builder for Algolia.

    Returns:
        Configured query builder
    """
    return SafeQueryBuilder(AlgoliaBackend())


__all__ = [
    "AlgoliaBackend",
    "ElasticsearchBackend",
    "QueryBackend",
    "SafeQueryBuilder",
    "create_algolia_builder",
    "create_elasticsearch_builder",
]
