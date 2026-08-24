"""Registry-based dispatch of canonical filters to dialect renderers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.search.backends.filters._elasticsearch import (
    render_elasticsearch,
    render_opensearch,
)
from lexigram.search.backends.filters._meilisearch import render_meilisearch
from lexigram.search.backends.filters._memory import render_memory
from lexigram.search.backends.filters._mongodb import render_mongodb
from lexigram.search.backends.filters._sql import (
    render_mysql,
    render_postgres,
    render_sqlite,
)
from lexigram.search.backends.filters._typesense import render_typesense
from lexigram.search.backends.filters._validation import FilterRenderError

_RENDERERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "elasticsearch": render_elasticsearch,
    "opensearch": render_opensearch,
    "meilisearch": render_meilisearch,
    "typesense": render_typesense,
    "mongodb": render_mongodb,
    "postgres": render_postgres,
    "mysql": render_mysql,
    "sqlite": render_sqlite,
    "memory": render_memory,
}


def render_filters(dialect: str, filters: dict[str, Any]) -> Any:
    """Render a canonical filter dict for a named backend dialect.

    Args:
        dialect: Backend dialect name (``elasticsearch``, ``opensearch``,
            ``meilisearch``, ``typesense``, ``mongodb``, ``postgres``,
            ``mysql``, ``sqlite``, ``memory``).
        filters: Canonical filter dict to render.

    Returns:
        Backend-native filter representation: ES/OpenSearch clause list,
        Meilisearch/Typesense filter string, MongoDB query document,
        SQL ``(clause, params)`` pair, or the validated dict itself for
        in-memory backends.

    Raises:
        FilterRenderError: If the dialect is unknown or the filter dict
            violates the canonical dialect.
    """
    renderer = _RENDERERS.get(dialect)
    if renderer is None:
        raise FilterRenderError(f"unknown filter dialect {dialect!r}")
    return renderer(filters)
