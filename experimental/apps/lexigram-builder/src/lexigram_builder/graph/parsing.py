"""Graph parsing — serialize and deserialize ``GraphDocument`` dicts.

``parse_document`` turns a raw JSON dict into typed model objects;
``document_to_dict`` round-trips them back.  Both functions must have
a branch for every ``NodeConfig`` variant — missing branches cause
silent data loss on save/reload.
"""

from __future__ import annotations

from typing import Any

from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    EntityConfig,
    FeatureFlagConfig,
    JobConfig,
    MiddlewareConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    RouteGroupConfig,
    ServiceConfig,
)
from lexigram_builder.graph.palette import (
    KIND_AUTH,
    KIND_CONTRACT,
    KIND_ENTITY,
    KIND_FEATURE_FLAG,
    KIND_JOB,
    KIND_MIDDLEWARE,
    KIND_RATE_LIMIT,
    KIND_ROLE,
    KIND_ROUTE,
    KIND_ROUTE_GROUP,
    KIND_SERVICE,
)


def _coerce_tuple(value: Any) -> tuple[str, ...]:
    """Coerce a JSON list (or comma-separated string) to a tuple of strings."""
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return ()


def parse_node_config(kind: str, raw: dict[str, Any]) -> Any:
    """Parse a raw config dict into the appropriate frozen dataclass.

    Args:
        kind: The node kind string (e.g. ``"feature_flag"``).
        raw: The ``config`` portion of the node dict.

    Returns:
        A frozen dataclass instance.

    Raises:
        ValueError: If *kind* is unknown.
    """
    if kind == KIND_ROUTE:
        return RouteConfig(
            path=raw.get("path", "/api/items"),
            ops=tuple(raw.get("ops", ("create", "get", "list", "update", "delete"))),
            path_prefix=raw.get("path_prefix", ""),
        )
    if kind == KIND_ROUTE_GROUP:
        return RouteGroupConfig(prefix=raw.get("prefix", "/api"))
    if kind == KIND_ENTITY:
        return EntityConfig(
            name=raw.get("name", "item"),
            fields=raw.get("fields", "name:str, description:str?"),
        )
    if kind == KIND_SERVICE:
        return ServiceConfig(name=raw.get("name", "item_service"))
    if kind == KIND_JOB:
        return JobConfig(
            name=raw.get("name", "process_items"),
            schedule=raw.get("schedule", "0 * * * *"),
        )
    if kind == KIND_MIDDLEWARE:
        return MiddlewareConfig(name=raw.get("name", "cors"))
    if kind == KIND_FEATURE_FLAG:
        return FeatureFlagConfig(
            name=raw.get("name", "new_checkout"),
            enabled=bool(raw.get("enabled", True)),
            description=raw.get("description", ""),
        )
    if kind == KIND_AUTH:
        return AuthConfig(
            name=raw.get("name", "jwt_auth"),
            provider=raw.get("provider", "jwt"),
        )
    if kind == KIND_ROLE:
        return RoleConfig(
            name=raw.get("name", "admin"),
            permissions=_coerce_tuple(raw.get("permissions", ())),
            inherits=raw.get("inherits", ""),
        )
    if kind == KIND_RATE_LIMIT:
        return RateLimitConfig(
            name=raw.get("name", "api_rate_limit"),
            strategy=raw.get("strategy", "sliding_window"),
            max_requests=int(raw.get("max_requests", 100)),
            window_seconds=int(raw.get("window_seconds", 60)),
        )
    if kind == KIND_CONTRACT:
        return ContractConfig(
            name=raw.get("name", "create_order"),
            direction=raw.get("direction", "request"),
            fields=raw.get("fields", "item_id:str, quantity:int"),
            entity=raw.get("entity", ""),
            enabled=bool(raw.get("enabled", True)),
            description=raw.get("description", ""),
        )
    raise ValueError(f"Unknown node kind: {kind!r}")


def config_to_dict(kind: str, config: Any) -> dict[str, Any]:
    """Serialize a config dataclass back to a JSON-safe dict.

    Args:
        kind: The node kind string.
        config: A frozen dataclass instance (one of the ``NodeConfig`` variants).

    Returns:
        A plain dict suitable for JSON serialization.

    Raises:
        ValueError: If *kind* is unknown.
    """
    if kind == KIND_ROUTE:
        return {
            "path": config.path,
            "ops": list(config.ops),
            "path_prefix": config.path_prefix,
        }
    if kind == KIND_ROUTE_GROUP:
        return {"prefix": config.prefix}
    if kind == KIND_ENTITY:
        return {"name": config.name, "fields": config.fields}
    if kind == KIND_SERVICE:
        return {"name": config.name}
    if kind == KIND_JOB:
        return {"name": config.name, "schedule": config.schedule}
    if kind == KIND_MIDDLEWARE:
        return {"name": config.name}
    if kind == KIND_FEATURE_FLAG:
        return {
            "name": config.name,
            "enabled": config.enabled,
            "description": config.description,
        }
    if kind == KIND_AUTH:
        return {"name": config.name, "provider": config.provider}
    if kind == KIND_ROLE:
        return {
            "name": config.name,
            "permissions": list(config.permissions),
            "inherits": config.inherits,
        }
    if kind == KIND_RATE_LIMIT:
        return {
            "name": config.name,
            "strategy": config.strategy,
            "max_requests": config.max_requests,
            "window_seconds": config.window_seconds,
        }
    if kind == KIND_CONTRACT:
        return {
            "name": config.name,
            "direction": config.direction,
            "fields": config.fields,
            "entity": config.entity,
            "enabled": config.enabled,
            "description": config.description,
        }
    raise ValueError(f"Unknown node kind: {kind!r}")


def parse_document(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse a full graph document dict into typed models.

    Returns a dict with ``"nodes"`` (list of parsed node dicts) and
    ``"edges"`` (list of edge dicts).  Each node dict has ``"id"``,
    ``"kind"``, and ``"config"`` (a frozen dataclass).
    """
    nodes: list[dict[str, Any]] = []
    for raw_node in raw.get("nodes", []):
        kind = raw_node["kind"]
        config = parse_node_config(kind, raw_node.get("config", {}))
        nodes.append(
            {
                "id": raw_node["id"],
                "kind": kind,
                "config": config,
            }
        )

    edges = list(raw.get("edges", []))

    return {"nodes": nodes, "edges": edges}


def document_to_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """Serialize a parsed graph document back to a JSON-safe dict.

    This is the inverse of :func:`parse_document`.  Every ``NodeConfig``
    variant must have a branch in :func:`config_to_dict` — missing
    branches cause ``config: null`` on save/reload.
    """
    nodes: list[dict[str, Any]] = []
    for node in doc.get("nodes", []):
        kind = node["kind"]
        config = config_to_dict(kind, node["config"])
        nodes.append(
            {
                "id": node["id"],
                "kind": kind,
                "config": config,
            }
        )

    return {"nodes": nodes, "edges": list(doc.get("edges", []))}


__all__ = [
    "config_to_dict",
    "document_to_dict",
    "parse_document",
    "parse_node_config",
]
