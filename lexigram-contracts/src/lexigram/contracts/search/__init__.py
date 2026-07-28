"""Search protocols and data models."""

from __future__ import annotations

from lexigram.contracts.search.protocols import (
    DatabaseSearchBackendProtocol,
    DocumentTransformerProtocol,
    IndexManagerProtocol,
    SearchableProtocol,
    SearchAnalyticsProtocol,
    SearchEngineProtocol,
)
from lexigram.contracts.search.types import (
    DocumentData,
    IndexSettings,
    SearchFilters,
    SearchIndexResult,
)

__all__ = [
    "DatabaseSearchBackendProtocol",
    "DocumentData",
    "DocumentTransformerProtocol",
    "IndexManagerProtocol",
    "IndexSettings",
    "SearchAnalyticsProtocol",
    "SearchEngineProtocol",
    "SearchFilters",
    "SearchIndexResult",
    "SearchableProtocol",
]
