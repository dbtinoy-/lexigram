"""Canonical search filter dialect and per-backend rendering.

All search backends receive one canonical filter dictionary shape via
``search(..., filters=...)``:

* ``{field: value}`` — equality predicate (a bare ``list`` value is
  treated as ``in``).
* ``{field: {"op": value}}`` — operator predicate with ``op`` one of
  ``in`` / ``nin`` / ``ne`` / ``gt`` / ``gte`` / ``lt`` / ``lte`` /
  ``contains`` / ``exists`` (multiple comparison keys such as
  ``{"gte": a, "lte": b}`` express a range).
* ``{"$and": [sub, ...]}``, ``{"$or": [sub, ...]}`` — boolean groups of
  sub-filter dicts.
* ``{"$not": sub}`` — negation of a sub-filter dict.

This module is the single place that renders that dialect into each
backend's native filter syntax.  Backends pick their renderer through
:func:`render_filters` (registry-based dispatch), keeping the canonical
form portable and the per-engine syntax isolated.
"""

from __future__ import annotations

from collections.abc import Callable

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
from lexigram.search.backends.filters._validation import (
    _FIELD_NAME_RE,  # noqa: PLC2701 — consumed by backend siblings
    FilterRenderError,
)
from lexigram.search.backends.filters.dispatch import render_filters

__all__ = [
    "FilterRenderError",
    "render_elasticsearch",
    "render_filters",
    "render_meilisearch",
    "render_memory",
    "render_mongodb",
    "render_mysql",
    "render_opensearch",
    "render_postgres",
    "render_sqlite",
    "render_typesense",
]
