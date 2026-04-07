"""Search Engine Backend Factory"""

from __future__ import annotations

from typing import Any

from lexigram.search import constants as search_const
from lexigram.search.backends.meilisearch import MeiliSearchBackend
from lexigram.search.backends.null import NullBackend

try:
    from lexigram.search.backends.sqlite import SQLiteSearchBackend

    _sqlite_available = True
except ImportError:
    _sqlite_available = False
    SQLiteSearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.mongodb import MongoSearchBackend

    _mongodb_available = True
except ImportError:
    _mongodb_available = False
    MongoSearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.elasticsearch import ElasticsearchBackend

    _elasticsearch_available = True
except ImportError:
    _elasticsearch_available = False
    ElasticsearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.opensearch import OpenSearchBackend

    _opensearch_available = True
except ImportError:
    _opensearch_available = False
    OpenSearchBackend = None  # type: ignore[misc,assignment]

try:
    from lexigram.search.backends.typesense import TypesenseBackend

    _typesense_available = True
except ImportError:
    _typesense_available = False
    TypesenseBackend = None  # type: ignore[misc,assignment]


def get_backend(backend_name: str, **config: Any) -> Any:
    """Factory function to create backend instances"""
    backends = {
        search_const.BACKEND_MEILISEARCH: MeiliSearchBackend,
        search_const.BACKEND_MEMORY: NullBackend,
    }

    if _sqlite_available:
        backends[search_const.BACKEND_SQLITE] = SQLiteSearchBackend

    if _mongodb_available:
        backends[search_const.BACKEND_MONGODB] = MongoSearchBackend

    if _elasticsearch_available:
        backends[search_const.BACKEND_ELASTICSEARCH] = ElasticsearchBackend

    if _opensearch_available:
        backends[search_const.BACKEND_OPENSEARCH] = OpenSearchBackend

    if _typesense_available:
        backends[search_const.BACKEND_TYPESENSE] = TypesenseBackend

    backend_class = backends.get(backend_name.lower())
    if not backend_class:
        raise ValueError(f"Unknown backend: {backend_name}")

    return backend_class(**config)


__all__ = ["get_backend"]
