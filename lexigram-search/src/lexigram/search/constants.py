"""Constants for lexigram-search."""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__ = importlib.metadata.version("lexigram-search")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_SEARCH__"
ENV_NESTED_DELIMITER: str = "__"

# -- Default Configuration Values --------------------------------------------

DEFAULT_BACKEND: str = "memory"
DEFAULT_MAX_RESULTS: int = 100
DEFAULT_PAGE_SIZE: int = 20
DEFAULT_MIN_SCORE: float = 0.0
DEFAULT_TIMEOUT: float = 5.0

# -- Backend Names -----------------------------------------------------------

BACKEND_MEILISEARCH: str = "meilisearch"
BACKEND_ELASTICSEARCH: str = "elasticsearch"
BACKEND_OPENSEARCH: str = "opensearch"
BACKEND_TYPESENSE: str = "typesense"
BACKEND_POSTGRES: str = "postgres"
BACKEND_MYSQL: str = "mysql"
BACKEND_SQLITE: str = "sqlite"
BACKEND_MONGODB: str = "mongodb"
BACKEND_MEMORY: str = "memory"

__all__ = [
    "BACKEND_ELASTICSEARCH",
    "BACKEND_MEILISEARCH",
    "BACKEND_MEMORY",
    "BACKEND_MONGODB",
    "BACKEND_MYSQL",
    "BACKEND_OPENSEARCH",
    "BACKEND_POSTGRES",
    "BACKEND_SQLITE",
    "BACKEND_TYPESENSE",
    "DEFAULT_BACKEND",
    "DEFAULT_MAX_RESULTS",
    "DEFAULT_MIN_SCORE",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_TIMEOUT",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]
