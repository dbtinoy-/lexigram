"""Search Engine Backends Package.

**Error propagation contract (D2.1)**

All search backend implementations return
``Result[SearchResponse, SearchError]`` for domain-level outcomes — they
never raise exceptions to signal that a query returned no results, a
document was not found, or an index does not exist.

Infrastructure exceptions (network timeout, connection refused, TLS
errors, etc.) are **not** wrapped in ``Result`` and propagate as
exceptions.  The calling layer is responsible for catching and mapping
these to an appropriate error response.

Implementing a new backend:

* Subclass :class:`~lexigram.search.backends.base.SearchBackendBase`.
* Return ``Ok(response)`` on success and ``Err(SearchError(...))`` on
  domain-level failure.
* Let infrastructure exceptions bubble up unchanged.
"""

from __future__ import annotations

from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.backends.factory import get_backend
from lexigram.search.backends.meilisearch import MeiliSearchBackend
from lexigram.search.backends.mysql import MySQLDatabaseSearchBackend
from lexigram.search.backends.null import NullBackend
from lexigram.search.backends.postgres import PostgresDatabaseSearchBackend

try:
    from lexigram.search.backends.sqlite import SQLiteSearchBackend
except ImportError:
    SQLiteSearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.mongodb import MongoSearchBackend
except ImportError:
    MongoSearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.elasticsearch import ElasticsearchBackend
except ImportError:
    ElasticsearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.opensearch import OpenSearchBackend
except ImportError:
    OpenSearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.typesense import TypesenseBackend
except ImportError:
    TypesenseBackend = None  # type: ignore[misc,assignment]

__all__ = [
    "ElasticsearchBackend",
    "MeiliSearchBackend",
    "MongoSearchBackend",
    "MySQLDatabaseSearchBackend",
    "NullBackend",
    "OpenSearchBackend",
    "PostgresDatabaseSearchBackend",
    "SQLiteSearchBackend",
    "SearchBackendBase",
    "TypesenseBackend",
    "get_backend",
]
