"""Graph validation — check nodes and edges for correctness.

Each node kind has a ``_check_<kind>`` function dispatched from
``check_node``.  Kinds without a check currently fall through to
``return []`` — add a real check for anything with a snake_case ``name``
or a constrained field.
"""

from __future__ import annotations

import re
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
    ALLOWED_EDGES,
    KNOWN_KINDS,
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

# ── Helpers ───────────────────────────────────────────────────────────

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# Valid field types for entity/contract fields.
FIELD_TYPES: frozenset[str] = frozenset(
    {
        "str",
        "int",
        "float",
        "bool",
        "datetime",
        "date",
        "uuid",
        "decimal",
        "text",
        "json",
        "list",
        "dict",
    }
)

# Valid auth providers.
AUTH_PROVIDERS: frozenset[str] = frozenset({"jwt", "api_key", "oauth2", "session"})

# Valid rate-limit strategies.
RATE_LIMIT_STRATEGIES: frozenset[str] = frozenset(
    {"sliding_window", "fixed_window", "token_bucket"}
)

# Valid contract directions.
CONTRACT_DIRECTIONS: frozenset[str] = frozenset({"request", "response", "both"})


def is_snake_case_identifier(value: str) -> bool:
    """Return ``True`` if *value* is a valid snake_case Python identifier."""
    return bool(_SNAKE_CASE_RE.fullmatch(value))


def _parse_field_spec(fields_str: str) -> list[tuple[str, str]]:
    """Parse a ``name:type`` field spec string into ``(name, type)`` pairs."""
    fields: list[tuple[str, str]] = []
    for part in fields_str.split(","):
        part = part.strip()
        if not part:
            continue
        # Strip optional markers (?, !, =default)
        clean = re.sub(r"[?!].*$", "", part).strip()
        if ":" not in clean:
            continue
        name, ftype = clean.split(":", 1)
        fields.append((name.strip(), ftype.strip()))
    return fields


# ── Per-kind checks ───────────────────────────────────────────────────


def _check_route(config: RouteConfig) -> list[str]:
    errors: list[str] = []
    if not config.path.startswith("/"):
        errors.append("route.path must start with '/'")
    valid_ops = {"create", "get", "list", "update", "delete"}
    unknown = set(config.ops) - valid_ops
    if unknown:
        errors.append(f"route.ops contains unknown operations: {sorted(unknown)}")
    return errors


def _check_route_group(config: RouteGroupConfig) -> list[str]:
    errors: list[str] = []
    if not config.prefix.startswith("/"):
        errors.append("route_group.prefix must start with '/'")
    return errors


def _check_entity(config: EntityConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"entity.name must be snake_case identifier, got {config.name!r}"
        )
    for field_name, ftype in _parse_field_spec(config.fields):
        if ftype not in FIELD_TYPES:
            errors.append(
                f"entity field {field_name!r} has unknown type {ftype!r}; "
                f"expected one of {sorted(FIELD_TYPES)}"
            )
    return errors


def _check_service(config: ServiceConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"service.name must be snake_case identifier, got {config.name!r}"
        )
    return errors


def _check_job(config: JobConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(f"job.name must be snake_case identifier, got {config.name!r}")
    if not config.schedule:
        errors.append("job.schedule must not be empty")
    return errors


def _check_middleware(config: MiddlewareConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"middleware.name must be snake_case identifier, got {config.name!r}"
        )
    return errors


def _check_feature_flag(config: FeatureFlagConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"feature_flag.name must be snake_case identifier, got {config.name!r}"
        )
    return errors


def _check_auth(config: AuthConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"auth.name must be snake_case identifier, got {config.name!r}"
        )
    if config.provider not in AUTH_PROVIDERS:
        errors.append(
            f"auth.provider must be one of {sorted(AUTH_PROVIDERS)}, "
            f"got {config.provider!r}"
        )
    return errors


def _check_role(config: RoleConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"role.name must be snake_case identifier, got {config.name!r}"
        )
    if config.inherits and not is_snake_case_identifier(config.inherits):
        errors.append(
            f"role.inherits must be snake_case identifier, got {config.inherits!r}"
        )
    return errors


def _check_rate_limit(config: RateLimitConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"rate_limit.name must be snake_case identifier, got {config.name!r}"
        )
    if config.strategy not in RATE_LIMIT_STRATEGIES:
        errors.append(
            f"rate_limit.strategy must be one of {sorted(RATE_LIMIT_STRATEGIES)}, "
            f"got {config.strategy!r}"
        )
    if config.max_requests <= 0:
        errors.append(
            f"rate_limit.max_requests must be positive, got {config.max_requests}"
        )
    if config.window_seconds <= 0:
        errors.append(
            f"rate_limit.window_seconds must be positive, got {config.window_seconds}"
        )
    return errors


def _check_contract(config: ContractConfig) -> list[str]:
    errors: list[str] = []
    if not is_snake_case_identifier(config.name):
        errors.append(
            f"contract.name must be snake_case identifier, got {config.name!r}"
        )
    if config.direction not in CONTRACT_DIRECTIONS:
        errors.append(
            f"contract.direction must be one of {sorted(CONTRACT_DIRECTIONS)}, "
            f"got {config.direction!r}"
        )
    if config.direction != "both" and not config.fields and not config.entity:
        errors.append(
            "contract.fields must be non-empty when direction is not 'both' "
            "and no entity is referenced"
        )
    for field_name, ftype in _parse_field_spec(config.fields):
        if ftype not in FIELD_TYPES:
            errors.append(
                f"contract field {field_name!r} has unknown type {ftype!r}; "
                f"expected one of {sorted(FIELD_TYPES)}"
            )
    return errors


# ── Dispatch ──────────────────────────────────────────────────────────

_KIND_CHECKERS: dict[str, Any] = {
    KIND_ROUTE: _check_route,
    KIND_ROUTE_GROUP: _check_route_group,
    KIND_ENTITY: _check_entity,
    KIND_SERVICE: _check_service,
    KIND_JOB: _check_job,
    KIND_MIDDLEWARE: _check_middleware,
    KIND_FEATURE_FLAG: _check_feature_flag,
    KIND_AUTH: _check_auth,
    KIND_ROLE: _check_role,
    KIND_RATE_LIMIT: _check_rate_limit,
    KIND_CONTRACT: _check_contract,
}


def check_node(kind: str, config: Any) -> list[str]:
    """Validate a single node.

    Returns a list of error strings (empty means valid).
    """
    if kind not in KNOWN_KINDS:
        return [f"Unknown node kind: {kind!r}"]

    checker = _KIND_CHECKERS.get(kind)
    if checker is None:
        return []
    return checker(config)


def check_edge(source_kind: str, target_kind: str) -> list[str]:
    """Validate a single edge.

    Returns a list of error strings (empty means valid).
    """
    if (source_kind, target_kind) not in ALLOWED_EDGES:
        return [
            f"Edge ({source_kind!r}, {target_kind!r}) is not in ALLOWED_EDGES"
        ]
    return []


def check_document(doc: dict[str, Any]) -> list[str]:
    """Validate a full parsed graph document.

    Returns a list of all error strings.
    """
    errors: list[str] = []

    for node in doc.get("nodes", []):
        kind = node.get("kind", "")
        config = node.get("config")
        node_id = node.get("id", "?")
        node_errors = check_node(kind, config)
        for err in node_errors:
            errors.append(f"Node {node_id} ({kind}): {err}")

    for edge in doc.get("edges", []):
        source_id = edge.get("source", "")
        target_id = edge.get("target", "")
        # Resolve kinds from node ids
        node_map = {n["id"]: n for n in doc.get("nodes", [])}
        source_node = node_map.get(source_id)
        target_node = node_map.get(target_id)
        if source_node is None:
            errors.append(f"Edge references unknown source node: {source_id!r}")
            continue
        if target_node is None:
            errors.append(f"Edge references unknown target node: {target_id!r}")
            continue
        edge_errors = check_edge(source_node["kind"], target_node["kind"])
        for err in edge_errors:
            errors.append(f"Edge ({source_id} → {target_id}): {err}")

    return errors


__all__ = [
    "AUTH_PROVIDERS",
    "CONTRACT_DIRECTIONS",
    "FIELD_TYPES",
    "RATE_LIMIT_STRATEGIES",
    "check_document",
    "check_edge",
    "check_node",
    "is_snake_case_identifier",
]
