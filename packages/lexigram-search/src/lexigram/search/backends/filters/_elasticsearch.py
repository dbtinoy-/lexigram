"""Elasticsearch/OpenSearch filter rendering."""

from __future__ import annotations

from typing import Any

from lexigram.search.backends.filters._validation import (
    FilterRenderError,
    _validate_filters,
)


def _es_clauses(sub: dict[str, Any]) -> list[dict[str, Any]]:
    """Render one sub-filter dict to an ES clause list (AND semantics)."""
    clauses: list[dict[str, Any]] = []
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            clauses.append({"bool": {"must_not": _es_clauses(value)}})
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            groups = [item for group in value for item in _es_clauses(group)]
            if key == "$or":
                clauses.append({"bool": {"should": groups, "minimum_should_match": 1}})
            else:
                clauses.extend(groups)
            continue
        if isinstance(value, dict):
            if "contains" in value:
                clauses.append(
                    {
                        "wildcard": {
                            key: {
                                "value": f"*{value['contains']}*",
                                "case_insensitive": True,
                            }
                        }
                    }
                )
                continue
            if "exists" in value:
                exists_clause = {"exists": {"field": key}}
                clauses.append(
                    exists_clause
                    if value["exists"]
                    else {"bool": {"must_not": exists_clause}}
                )
                continue
            if "in" in value:
                clauses.append({"terms": {key: list(value["in"])}})
                continue
            if "nin" in value:
                clauses.append(
                    {"bool": {"must_not": [{"terms": {key: list(value["nin"])}}]}}
                )
                continue
            if "ne" in value:
                clauses.append({"bool": {"must_not": [{"term": {key: value["ne"]}}]}})
                continue
            clauses.append({"range": {key: value}})
            continue
        if isinstance(value, (list, tuple)):
            clauses.append({"terms": {key: list(value)}})
        else:
            clauses.append({"term": {key: value}})
    return clauses


def render_elasticsearch(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Render a filter dict to Elasticsearch ``bool`` filter clauses.

    Args:
        filters: Canonical filter dict.

    Returns:
        A list of ES query clauses; the caller wraps them in
        ``{"bool": {"filter": [...]}}`` (or ``must`` when empty).

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    _validate_filters(filters)
    return _es_clauses(filters)


def render_opensearch(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Render a filter dict to OpenSearch ``bool`` filter clauses.

    OpenSearch shares the Elasticsearch query DSL; see
    :func:`render_elasticsearch`.
    """
    return render_elasticsearch(filters)


# ---------------------------------------------------------------------------
# Meilisearch (filter-expression string)
# ---------------------------------------------------------------------------


