"""Package constants for lexigram-tenancy."""

from __future__ import annotations

import importlib.metadata

try:
    __version__ = importlib.metadata.version("lexigram-tenancy")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

# Environment variable configuration
ENV_PREFIX: str = "LEX_TENANCY__"
ENV_NESTED_DELIMITER: str = "__"

# Default header name used by HeaderTenantResolver
DEFAULT_HEADER_NAME: str = "x-tenant-id"

# Default path pattern used by PathTenantResolver
DEFAULT_PATH_PATTERN: str = "/tenants/{tenant_id}/"

# Default JWT claim key used by JWTClaimTenantResolver
DEFAULT_JWT_CLAIM_KEY: str = "tenant_id"

# Default validator cache TTL in seconds
DEFAULT_VALIDATOR_CACHE_TTL: int = 300

# Default config override cache TTL in seconds
DEFAULT_CONFIG_CACHE_TTL: int = 60

__all__ = [
    "DEFAULT_CONFIG_CACHE_TTL",
    "DEFAULT_HEADER_NAME",
    "DEFAULT_JWT_CLAIM_KEY",
    "DEFAULT_PATH_PATTERN",
    "DEFAULT_VALIDATOR_CACHE_TTL",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
