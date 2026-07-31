"""Query translator base class for converting SearchQuery to backend-specific queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from lexigram.search.backends.filters import _FIELD_NAME_RE


@dataclass
class TranslatedQuery:
    """Result of translating a SearchQuery to backend-specific query."""

    # The main query string/clause
    query: Any

    # Query parameters for prepared statements
    params: list[Any]

    # Additional options (limit, offset, etc.)
    options: dict[str, Any]

    # Aggregation/facet definitions
    aggregations: dict[str, Any] | None = None

    # Highlight definitions
    highlights: dict[str, Any] | None = None


class QueryTranslator(ABC):
    """Abstract base class for query translators.

    Each backend implements this to translate the unified SearchQuery
    into backend-specific query syntax.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def translate_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        sort: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> TranslatedQuery:
        """Translate a search query to backend-specific format.

        Args:
            query: The search query string
            filters: Optional filters to apply
            sort: Optional sort specifications
            limit: Maximum results to return
            offset: Result offset for pagination
            **kwargs: Additional backend-specific options

        Returns:
            TranslatedQuery with backend-specific query
        """

    @abstractmethod
    def translate_faceted_search(
        self,
        query: str,
        facets: list[str],
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> TranslatedQuery:
        """Translate a faceted search query.

        Args:
            query: The search query string
            facets: List of fields to facet on
            filters: Optional filters
            limit: Maximum results
            offset: Result offset
            **kwargs: Additional options

        Returns:
            TranslatedQuery with aggregations
        """

    @abstractmethod
    def translate_highlight(
        self,
        fields: list[str],
        pre_tags: list[str] | None = None,
        post_tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Translate highlight request.

        Args:
            fields: Fields to highlight
            pre_tags: Tags before highlighted text
            post_tags: Tags after highlighted text

        Returns:
            Backend-specific highlight configuration
        """


class PostgresQueryTranslator(QueryTranslator):
    """PostgreSQL query translator."""

    def __init__(self, text_search_config: str = "english", **config: Any) -> None:
        super().__init__(config)
        self.text_search_config = text_search_config

    def translate_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        sort: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> TranslatedQuery:
        """Translate to PostgreSQL full-text search query."""
        from lexigram import serialization as json

        sql_parts = [
            "SELECT id, document, ts_rank(search_vector, websearch_to_tsquery($1, $2)) AS score",
            "FROM search_{index}",
            "WHERE search_vector @@ websearch_to_tsquery($1, $2)",
        ]

        params = [self.text_search_config, query]

        # Add filters
        if filters:
            sql_parts.append("AND document @> $" + str(len(params) + 1))
            params.append(json.dumps(filters))  # type: ignore[arg-type]

        # Add sort
        if sort:
            # Parse sort fields
            order_parts = []
            for s in sort:
                if s.startswith("-"):
                    order_parts.append(f"document->>'{s[1:]}' DESC")
                else:
                    order_parts.append(f"document->>'{s}' ASC")
            sql_parts.append("ORDER BY " + ", ".join(order_parts))
        else:
            sql_parts.append("ORDER BY score DESC")

        # Add pagination
        sql_parts.append(f"LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}")
        params.append(str(limit))
        params.append(str(offset))

        return TranslatedQuery(
            query="\n".join(sql_parts),
            params=params,
            options={"limit": limit, "offset": offset},
        )

    def translate_faceted_search(
        self,
        query: str,
        facets: list[str],
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> TranslatedQuery:
        """Translate to PostgreSQL faceted search query."""
        # Similar to translate_search but with GROUP BY aggregations
        search_query = self.translate_search(query, filters, None, limit, offset)

        # Build facet queries
        aggregations = {}
        for facet in facets:
            if not _FIELD_NAME_RE.fullmatch(facet):
                raise ValueError(f"Invalid facet field: {facet!r}")
            aggregations[facet] = f"""
                SELECT document->>'{facet}' AS value, COUNT(*) AS count
                FROM search_{{index}}
                WHERE search_vector @@ websearch_to_tsquery($1, $2)
                GROUP BY document->>'{facet}'
                ORDER BY count DESC
            """  # noqa: S608 -- facet validated by _FIELD_NAME_RE

        return TranslatedQuery(
            query=search_query.query,
            params=search_query.params,
            options=search_query.options,
            aggregations=aggregations,
        )

    def translate_highlight(
        self,
        fields: list[str],
        pre_tags: list[str] | None = None,
        post_tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """PostgreSQL doesn't support native highlighting, return empty."""
        # PostgreSQL would need to use ts_headline function
        return {
            "use_ts_headline": True,
            "fields": {f: {} for f in fields},
        }


class ElasticsearchQueryTranslator(QueryTranslator):
    """Elasticsearch query translator."""

    def translate_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        sort: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> TranslatedQuery:
        """Translate to Elasticsearch query DSL."""
        # Build the query
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "name^2", "description", "content"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                },
            },
            "from": offset,
            "size": limit,
        }

        # Add filters
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                if isinstance(value, (list, tuple)):
                    filter_clauses.append({"terms": {key: value}})
                else:
                    filter_clauses.append({"term": {key: value}})

            search_body["query"] = {
                "bool": {
                    "must": search_body["query"],
                    "filter": filter_clauses,
                },
            }

        # Add sort
        if sort:
            search_body["sort"] = sort

        return TranslatedQuery(
            query=search_body,
            params=[],
            options={"limit": limit, "offset": offset},
        )

    def translate_faceted_search(
        self,
        query: str,
        facets: list[str],
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> TranslatedQuery:
        """Translate to Elasticsearch faceted search."""
        search_query = self.translate_search(query, filters, None, limit, offset)

        # Add aggregations
        aggregations = {}
        for facet in facets:
            aggregations[facet] = {
                "terms": {"field": facet, "size": 10},
            }

        return TranslatedQuery(
            query=search_query.query,
            params=search_query.params,
            options=search_query.options,
            aggregations=aggregations,
        )

    def translate_highlight(
        self,
        fields: list[str],
        pre_tags: list[str] | None = None,
        post_tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Translate to Elasticsearch highlight configuration."""
        if pre_tags is None:
            pre_tags = ["<mark>"]
        if post_tags is None:
            post_tags = ["</mark>"]

        highlights = {
            "fields": {field: {} for field in fields},
            "pre_tags": pre_tags,
            "post_tags": post_tags,
        }

        return highlights


__all__ = [
    "ElasticsearchQueryTranslator",
    "PostgresQueryTranslator",
    "QueryTranslator",
    "TranslatedQuery",
]
