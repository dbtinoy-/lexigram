"""Pre-built analyzer configurations for Elasticsearch."""

from __future__ import annotations

from typing import Any


class ElasticsearchAnalyzers:
    """Pre-built analyzer configurations for Elasticsearch."""

    # Standard analyzer with lowercase and asciifolding
    STANDARD_ANALYZER = {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase", "asciifolding"],
    }

    # Analyzer for autocomplete
    AUTOCOMPLETE_ANALYZER = {
        "type": "custom",
        "tokenizer": "standard",
        "filter": [
            "lowercase",
            "asciifolding",
            "autocomplete_filter",
        ],
    }

    # Analyzer for edge n-grams (prefix matching)
    EDGE_NGRAM_ANALYZER = {
        "type": "custom",
        "tokenizer": "standard",
        "filter": [
            "lowercase",
            "asciifolding",
            "edge_ngram_filter",
        ],
    }

    # Analyzer for language-specific stemming
    ENGLISH_ANALYZER = {
        "type": "custom",
        "tokenizer": "standard",
        "filter": [
            "lowercase",
            "asciifolding",
            "english_stemmer",
            "english_possessive_filter",
        ],
    }

    # Token filters
    AUTOCOMPLETE_FILTER = {
        "type": "edge_ngram",
        "min_gram": 2,
        "max_gram": 20,
    }

    EDGE_NGRAM_FILTER = {
        "type": "edge_ngram",
        "min_gram": 2,
        "max_gram": 10,
    }

    ENGLISH_STEMMER = {
        "type": "stemmer",
        "language": "english",
    }

    ENGLISH_POSSESSIVE_FILTER = {
        "type": "possessive",
        "language": "english",
    }

    @classmethod
    def get_settings(cls, analyzer_name: str = "standard") -> dict:
        """Get analyzer settings by name."""
        analyzers = {
            "standard": cls.STANDARD_ANALYZER,
            "autocomplete": cls.AUTOCOMPLETE_ANALYZER,
            "edge_ngram": cls.EDGE_NGRAM_ANALYZER,
            "english": cls.ENGLISH_ANALYZER,
        }

        filters = {
            "autocomplete_filter": cls.AUTOCOMPLETE_FILTER,
            "edge_ngram_filter": cls.EDGE_NGRAM_FILTER,
            "english_stemmer": cls.ENGLISH_STEMMER,
            "english_possessive_filter": cls.ENGLISH_POSSESSIVE_FILTER,
        }

        analyzer = analyzers.get(analyzer_name, cls.STANDARD_ANALYZER)

        return {
            "analysis": {
                "analyzer": {analyzer_name: analyzer},
                "filter": filters,
            },
        }

    @classmethod
    def get_all_settings(cls) -> dict:
        """Get all analyzer settings."""
        return {
            "analysis": {
                "analyzer": {
                    "standard": cls.STANDARD_ANALYZER,
                    "autocomplete": cls.AUTOCOMPLETE_ANALYZER,
                    "edge_ngram": cls.EDGE_NGRAM_ANALYZER,
                    "english": cls.ENGLISH_ANALYZER,
                },
                "filter": {
                    "autocomplete_filter": cls.AUTOCOMPLETE_FILTER,
                    "edge_ngram_filter": cls.EDGE_NGRAM_FILTER,
                    "english_stemmer": cls.ENGLISH_STEMMER,
                    "english_possessive_filter": cls.ENGLISH_POSSESSIVE_FILTER,
                },
            },
        }

    @classmethod
    def get_autocomplete_field_definition(cls) -> dict:
        """Get field definition for autocomplete."""
        return {
            "type": "text",
            "analyzer": "autocomplete",
            "search_analyzer": "standard",
        }

    @classmethod
    def get_edge_ngram_field_definition(cls) -> dict:
        """Get field definition for edge n-gram matching."""
        return {
            "type": "text",
            "analyzer": "edge_ngram",
            "search_analyzer": "standard",
        }


# Pre-defined field boosting weights
FIELD_BOOSTS = {
    "title": 3.0,
    "name": 2.0,
    "description": 1.0,
    "content": 1.0,
    "text": 1.0,
    "body": 1.0,
}


def build_multi_match_query(
    query: str,
    fields: dict[str, float] | None = None,
    query_type: str = "best_fields",
    fuzziness: str = "AUTO",
) -> dict:
    """Build a multi_match query with field boosts.

    Args:
        query: The search query
        fields: Dict of field names to boost values
        query_type: Type of multi_match query
        fuzziness: Fuzziness level

    Returns:
        Elasticsearch query dict
    """
    if fields is None:
        fields = FIELD_BOOSTS

    # Build fields list with boosts
    fields_list = [
        f"^{boost}" if boost != 1.0 else field for field, boost in fields.items()
    ]

    return {
        "multi_match": {
            "query": query,
            "fields": fields_list,
            "type": query_type,
            "fuzziness": fuzziness,
        },
    }


def build_bool_query(
    must: list[dict] | None = None,
    should: list[dict] | None = None,
    filter: list[dict] | None = None,
    must_not: list[dict] | None = None,
    minimum_should_match: int | None = None,
) -> dict:
    """Build a bool query.

    Returns:
        Elasticsearch bool query dict
    """
    bool_query: dict[str, Any] = {}

    if must:
        bool_query["must"] = must
    if should:
        bool_query["should"] = should
    if filter:
        bool_query["filter"] = filter
    if must_not:
        bool_query["must_not"] = must_not
    if minimum_should_match is not None:
        bool_query["minimum_should_match"] = minimum_should_match

    return {"bool": bool_query}


def build_faceted_query(
    query: str,
    filters: dict[str, Any] | None = None,
    facets: dict[str, str] | None = None,
) -> dict:
    """Build a faceted search query.

    Args:
        query: The search query
        filters: Dict of field to filter values
        facets: Dict of field to aggregation type

    Returns:
        Elasticsearch query dict with aggregations
    """
    # Build the main query
    main_query = build_multi_match_query(query)

    # Build filter clauses
    filter_clauses = []
    if filters:
        for field, value in filters.items():
            if isinstance(value, (list, tuple)):
                filter_clauses.append({"terms": {field: value}})
            else:
                filter_clauses.append({"term": {field: value}})

    # Combine with bool query
    if filter_clauses:
        search_query = build_bool_query(
            must=[main_query],
            filter=filter_clauses,
        )
    else:
        search_query = main_query

    # Build aggregations
    aggs = {}
    if facets:
        for field, agg_type in facets.items():
            if agg_type == "terms":
                aggs[field] = {"terms": {"field": field, "size": 10}}
            elif agg_type == "range":
                aggs[field] = {"range": {"field": field}}
            # Add more types as needed

    return {
        "query": search_query,
        "aggs": aggs,
    }


__all__ = [
    "FIELD_BOOSTS",
    "ElasticsearchAnalyzers",
    "build_bool_query",
    "build_faceted_query",
    "build_multi_match_query",
]
