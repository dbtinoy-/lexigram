"""Constants for lexigram-graphql."""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-graphql")
except ImportError:
    __version__ = "0.0.0"

# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_GRAPHQL__"
ENV_NESTED_DELIMITER: str = "__"

# -- Default Configuration Values --------------------------------------------

DEFAULT_MAX_DEPTH: int = 10
DEFAULT_MAX_ALIASES: int = 15
DEFAULT_MAX_COMPLEXITY: int = 1000
DEFAULT_REQUESTS_PER_MINUTE: int = 60
DEFAULT_CACHE_MAX_AGE: int = 0
DEFAULT_SUBSCRIPTION_KEEPALIVE: int = 30

# -- Endpoint Paths ----------------------------------------------------------

DEFAULT_GRAPHQL_PATH: str = "/graphql"
DEFAULT_PLAYGROUND_PATH: str = "/graphql/playground"
# WebSocket endpoint for GraphQL subscriptions.  Historically this lived at
# "/graphql/ws" in the codebase; keep the constant aligned with the value
# used throughout the documentation and downstream projects.
DEFAULT_SUBSCRIPTIONS_PATH: str = "/graphql/ws"

# -- Protocol Constants ------------------------------------------------------

INTROSPECTION_QUERY_TYPE: str = "__schema"
TYPENAME_FIELD: str = "__typename"

__all__ = [
    "DEFAULT_CACHE_MAX_AGE",
    "DEFAULT_GRAPHQL_PATH",
    "DEFAULT_MAX_ALIASES",
    "DEFAULT_MAX_COMPLEXITY",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_PLAYGROUND_PATH",
    "DEFAULT_REQUESTS_PER_MINUTE",
    "DEFAULT_SUBSCRIPTIONS_PATH",
    "DEFAULT_SUBSCRIPTION_KEEPALIVE",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "INTROSPECTION_QUERY_TYPE",
    "TYPENAME_FIELD",
]
