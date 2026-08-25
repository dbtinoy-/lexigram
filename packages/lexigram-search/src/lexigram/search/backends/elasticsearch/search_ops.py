"""Search-side operations for the Elasticsearch backend.

Pure helpers to build request bodies and parse responses for full-text
search and aggregation queries. Consumed by
:class:`~lexigram.search.backends.elasticsearch.backend.ElasticsearchBackend`.
"""

from __future__ import annotations

from typing import Any

from lexigram.search.backends.filters import render_elasticsearch
from lexigram.search.filterset import merge_filters, rule_to_filters
from lexigram.search.types import SearchResponse, SearchResult


def build_search_body(query: str, offset: int, limit: int) -> dict[str, Any]:
    """Build the multi_match search body with highlighting and paging."""
    return {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",
                    "name^2",
                    "description",
                    "content",
                    "text",
                    "body",
                ],
                "type": "best_fields",
                "fuzziness": "AUTO",
            },
        },
        "from": offset,
        "size": limit,
        "highlight": {
            "fields": {
                "title": {},
                "description": {},
                "content": {},
                "body": {},
            },
        },
    }


def apply_search_filters(
    search_body: dict[str, Any],
    filters: dict[str, Any] | None,
    rule: str | None,
) -> None:
    """Merge filterset filters into the search body as bool filter clauses."""
    if filters or rule:
        merged = merge_filters(filters, rule_to_filters(rule))
        filter_clauses = render_elasticsearch(merged)

        if filter_clauses:
            search_body["query"] = {
                "bool": {
                    "must": search_body["query"],
                    "filter": filter_clauses,
                },
            }


def parse_search_response(
    response: dict[str, Any],
    query: str,
    offset: int,
    limit: int,
) -> SearchResponse:
    """Convert a raw Elasticsearch search response into a ``SearchResponse``."""
    hits = response["hits"]["hits"]
    results = []
    for hit in hits:
        results.append(
            SearchResult(
                id=str(hit["_id"]),
                score=float(hit["_score"] or 0.0),
                data={
                    **hit["_source"],
                    "_id": hit["_id"],
                    "_score": hit["_score"],
                },
                highlights=hit.get("highlight"),
            )
        )

    total = response["hits"]["total"]["value"]

    return SearchResponse(
        results=results,
        total=total,
        page=offset // limit + 1 if limit else 1,
        per_page=limit,
        query=query,
    )


def build_aggregate_body(
    query: str,
    aggs: dict[str, Any],
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """Build the multi_match aggregation (faceting) request body."""
    return {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",
                    "name^2",
                    "description",
                    "content",
                    "text",
                    "body",
                ],
            },
        },
        "aggs": aggs,
        "from": offset,
        "size": limit,
    }


def parse_aggregate_response(
    response: dict[str, Any],
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Convert a raw aggregation response into the flat result dict."""
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return {
        "hits": results,
        "total": response["hits"]["total"]["value"],
        "aggregations": response.get("aggregations", {}),
        "limit": limit,
        "offset": offset,
    }
