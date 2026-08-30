"""Graph models — frozen dataclasses for every node config type.

Each config is ``@dataclass(frozen=True, slots=True)`` so it can be
round-tripped through ``parse_document`` / ``document_to_dict`` without
mutation.  The ``NodeConfig`` union at the bottom is the dispatch target
for serialization and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union


# ── Existing node configs ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RouteConfig:
    """Configuration for a ``route`` node."""

    path: str = "/api/items"
    ops: tuple[str, ...] = ("create", "get", "list", "update", "delete")
    path_prefix: str = ""


@dataclass(frozen=True, slots=True)
class RouteGroupConfig:
    """Configuration for a ``route_group`` node."""

    prefix: str = "/api"


@dataclass(frozen=True, slots=True)
class EntityConfig:
    """Configuration for an ``entity`` node."""

    name: str = "item"
    fields: str = "name:str, description:str?"


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    """Configuration for a ``service`` node."""

    name: str = "item_service"


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Configuration for a ``job`` node."""

    name: str = "process_items"
    schedule: str = "0 * * * *"


@dataclass(frozen=True, slots=True)
class MiddlewareConfig:
    """Configuration for a ``middleware`` node."""

    name: str = "cors"


# ── Workstream A — Feature flag ───────────────────────────────────────


@dataclass(frozen=True, slots=True)
class FeatureFlagConfig:
    """Configuration for a ``feature_flag`` node (Workstream A).

    A flag node defines a feature flag that can gate routes or route
    groups.  ``enabled`` controls the default rollout; ``description``
    is a human-readable note surfaced in the generated code.
    """

    name: str = "new_checkout"
    enabled: bool = True
    description: str = ""


# ── Workstream B — Guard chain ────────────────────────────────────────

_AUTH_PROVIDERS: frozenset[str] = frozenset({"jwt", "api_key", "oauth2", "session"})


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """Configuration for an ``auth`` node (Workstream B).

    ``provider`` selects the authentication strategy; ``name`` is the
    snake_case identifier used in the generated guard module.
    """

    name: str = "jwt_auth"
    provider: str = "jwt"


@dataclass(frozen=True, slots=True)
class RoleConfig:
    """Configuration for a ``role`` node (Workstream B).

    ``permissions`` is a tuple of permission strings that the role
    grants.  ``inherits`` optionally references another role name for
    role chaining.
    """

    name: str = "admin"
    permissions: tuple[str, ...] = ()
    inherits: str = ""


_RATE_LIMIT_STRATEGIES: frozenset[str] = frozenset(
    {"sliding_window", "fixed_window", "token_bucket"}
)


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Configuration for a ``rate_limit`` node (Workstream B).

    ``strategy`` selects the algorithm; ``max_requests`` and
    ``window_seconds`` define the threshold.  v1 emits a definition-only
    scaffold; enforcement is a documented TODO.
    """

    name: str = "api_rate_limit"
    strategy: str = "sliding_window"
    max_requests: int = 100
    window_seconds: int = 60


# ── Workstream C — Contract / DTO ─────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ContractConfig:
    """Configuration for a ``contract`` node (Workstream C).

    ``direction`` controls whether the generated Pydantic model is a
    request schema, a response schema, or both.  ``fields`` uses the
    same ``name:type`` grammar as the ``model`` / ``command`` generators.
    ``entity`` optionally references an entity node for field reuse.
    """

    name: str = "create_order"
    direction: Literal["request", "response", "both"] = "request"
    fields: str = "item_id:str, quantity:int"
    entity: str = ""
    enabled: bool = True
    description: str = ""


# ── Union type ────────────────────────────────────────────────────────

NodeConfig = Union[
    RouteConfig,
    RouteGroupConfig,
    EntityConfig,
    ServiceConfig,
    JobConfig,
    MiddlewareConfig,
    FeatureFlagConfig,
    AuthConfig,
    RoleConfig,
    RateLimitConfig,
    ContractConfig,
]

__all__ = [
    "AuthConfig",
    "ContractConfig",
    "EntityConfig",
    "FeatureFlagConfig",
    "JobConfig",
    "MiddlewareConfig",
    "NodeConfig",
    "RateLimitConfig",
    "RoleConfig",
    "RouteConfig",
    "RouteGroupConfig",
    "ServiceConfig",
]
