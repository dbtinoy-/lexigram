"""Security module.

This module provides security features for GraphQL APIs,
including depth limiting, alias limiting, rate limiting, and permissions.

Note: Advanced features like weighted cost analysis and
APQ are in lexigram-ent-graphql.
"""

from __future__ import annotations

from typing import Any

from lexigram.graphql.security.alias import (
    AliasLimitExtension,
    AliasLimitValidator,
)
from lexigram.graphql.security.depth import (
    DepthLimitExtension,
    DepthLimitValidator,
    create_depth_limit,
)
from lexigram.graphql.security.extensions import RateLimitExtension
from lexigram.graphql.security.permissions import (
    AbstractPermission,
    AllowAny,
    DenyAll,
    IsAdmin,
    IsAuthenticated,
    IsOwner,
    IsOwnerOrAdmin,
    allow_any,
    deny_all,
    is_admin,
    is_authenticated,
    is_owner,
    is_owner_or_admin,
)

try:
    from lexigram.graphql.security.rate_limit import (
        RateLimitConfig,
        RateLimiter,
        UnifiedRateLimiter,
    )
except ImportError:
    RateLimiter: Any = None  # type: ignore[no-redef]
    UnifiedRateLimiter: Any = None  # type: ignore[no-redef]
    RateLimitConfig: Any = None  # type: ignore[no-redef]

__all__ = [
    # Permissions
    "AbstractPermission",
    # Alias
    "AliasLimitExtension",
    "AliasLimitValidator",
    "AllowAny",
    "DenyAll",
    # Depth
    "DepthLimitExtension",
    "DepthLimitValidator",
    "IsAdmin",
    "IsAuthenticated",
    "IsOwner",
    "IsOwnerOrAdmin",
    "RateLimitConfig",
    # Rate limit
    "RateLimitExtension",
    "RateLimiter",
    "UnifiedRateLimiter",
    "allow_any",
    "create_depth_limit",
    "deny_all",
    "is_admin",
    "is_authenticated",
    "is_owner",
    "is_owner_or_admin",
]
