"""Root hook payload surface for lexigram-search.

Defines canonical payload dataclasses for search engine lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SearchIndexedHook",
    "SearchQueryExecutedHook",
]


@dataclass(frozen=True, kw_only=True)
class SearchIndexedHook:
    """Payload fired when a document is added or updated in the search index.

    Attributes:
        index_name: Name of the search index that was written to.
        document_id: Identifier of the document that was indexed.
    """

    index_name: str
    document_id: str


@dataclass(frozen=True, kw_only=True)
class SearchQueryExecutedHook:
    """Payload fired after a search query is executed.

    Attributes:
        index_name: Name of the search index that was queried.
        query: The raw query string that was executed.
        result_count: Number of results returned.
    """

    index_name: str
    query: str
    result_count: int
