"""Palette — central registry of node kinds, ports, edges, and defaults.

Every new node kind must be registered here.  Missing entries cause:

* ``unknown kind`` validation errors (``KNOWN_KINDS``),
* silent drops on save (``document_to_dict`` needs the kind to dispatch),
* or pruned files after generation (``_prune_stale_generated``).

See ``docs/BACKEND_FRAMEWORK_PLAN.md`` §1 for the full reference map.
"""

from __future__ import annotations

from typing import Any

# ── Kind constants ────────────────────────────────────────────────────

KIND_ROUTE = "route"
KIND_ROUTE_GROUP = "route_group"
KIND_ENTITY = "entity"
KIND_SERVICE = "service"
KIND_JOB = "job"
KIND_MIDDLEWARE = "middleware"
KIND_FEATURE_FLAG = "feature_flag"
KIND_AUTH = "auth"
KIND_ROLE = "role"
KIND_RATE_LIMIT = "rate_limit"
KIND_CONTRACT = "contract"

# ── Known kinds ───────────────────────────────────────────────────────

KNOWN_KINDS: frozenset[str] = frozenset(
    {
        KIND_ROUTE,
        KIND_ROUTE_GROUP,
        KIND_ENTITY,
        KIND_SERVICE,
        KIND_JOB,
        KIND_MIDDLEWARE,
        KIND_FEATURE_FLAG,
        KIND_AUTH,
        KIND_ROLE,
        KIND_RATE_LIMIT,
        KIND_CONTRACT,
    }
)

# ── Port types ────────────────────────────────────────────────────────

PORT_TYPE_CONFIG_REF = "config_ref"
PORT_TYPE_ENTITY_REF = "entity_ref"
PORT_TYPE_DATA_FLOW = "data_flow"

PORT_TYPES: frozenset[str] = frozenset(
    {
        PORT_TYPE_CONFIG_REF,
        PORT_TYPE_ENTITY_REF,
        PORT_TYPE_DATA_FLOW,
    }
)

# Which port types can connect to which (source → set of valid targets).
PORT_COMPATIBILITY: dict[str, frozenset[str]] = {
    PORT_TYPE_CONFIG_REF: frozenset({PORT_TYPE_CONFIG_REF}),
    PORT_TYPE_ENTITY_REF: frozenset({PORT_TYPE_ENTITY_REF}),
    PORT_TYPE_DATA_FLOW: frozenset({PORT_TYPE_DATA_FLOW}),
}

# ── Per-kind port declarations ────────────────────────────────────────
# Each entry maps a kind to its ``(input_ports, output_ports)`` tuple.
# Port names are socket labels on the canvas node.

NODE_PORTS: dict[str, tuple[list[str], list[str]]] = {
    KIND_ROUTE: (
        ["entity", "policies"],  # inputs
        ["features", "guards"],  # outputs
    ),
    KIND_ROUTE_GROUP: (
        [],
        ["routes"],
    ),
    KIND_ENTITY: (
        [],
        ["ref"],
    ),
    KIND_SERVICE: (
        ["entity"],
        [],
    ),
    KIND_JOB: (
        ["entity"],
        [],
    ),
    KIND_MIDDLEWARE: (
        [],
        ["ref"],
    ),
    KIND_FEATURE_FLAG: (
        [],
        ["ref"],
    ),
    KIND_AUTH: (
        [],
        ["ref"],
    ),
    KIND_ROLE: (
        ["auth"],
        ["ref"],
    ),
    KIND_RATE_LIMIT: (
        [],
        ["ref"],
    ),
    KIND_CONTRACT: (
        ["entity"],
        ["ref"],
    ),
}

# ── Allowed edges ─────────────────────────────────────────────────────
# ``(source_kind, target_kind)`` pairs that the validator accepts.

ALLOWED_EDGES: frozenset[tuple[str, str]] = frozenset(
    {
        # Entity wiring
        (KIND_ROUTE, KIND_ENTITY),
        (KIND_SERVICE, KIND_ENTITY),
        (KIND_JOB, KIND_ENTITY),
        (KIND_CONTRACT, KIND_ENTITY),
        # Feature flag gating
        (KIND_ROUTE, KIND_FEATURE_FLAG),
        (KIND_ROUTE_GROUP, KIND_FEATURE_FLAG),
        # Guard chain
        (KIND_ROUTE, KIND_AUTH),
        (KIND_ROUTE, KIND_ROLE),
        (KIND_ROUTE, KIND_RATE_LIMIT),
        (KIND_ROLE, KIND_AUTH),
        # Contract wiring
        (KIND_ROUTE, KIND_CONTRACT),
        # Middleware
        (KIND_ROUTE, KIND_MIDDLEWARE),
        (KIND_ROUTE_GROUP, KIND_MIDDLEWARE),
    }
)

# Maps ``(source, target)`` edge pairs to a human-readable edge kind label.
EDGE_KIND_MAP: dict[tuple[str, str], str] = {
    (KIND_ROUTE, KIND_ENTITY): "route_to_entity",
    (KIND_SERVICE, KIND_ENTITY): "service_to_entity",
    (KIND_JOB, KIND_ENTITY): "job_to_entity",
    (KIND_CONTRACT, KIND_ENTITY): "contract_to_entity",
    (KIND_ROUTE, KIND_FEATURE_FLAG): "route_to_feature_flag",
    (KIND_ROUTE_GROUP, KIND_FEATURE_FLAG): "route_group_to_feature_flag",
    (KIND_ROUTE, KIND_AUTH): "route_to_auth",
    (KIND_ROUTE, KIND_ROLE): "route_to_role",
    (KIND_ROUTE, KIND_RATE_LIMIT): "route_to_rate_limit",
    (KIND_ROLE, KIND_AUTH): "role_to_auth",
    (KIND_ROUTE, KIND_CONTRACT): "route_to_contract",
    (KIND_ROUTE, KIND_MIDDLEWARE): "route_to_middleware",
    (KIND_ROUTE_GROUP, KIND_MIDDLEWARE): "route_group_to_middleware",
}

# ── Node defaults ─────────────────────────────────────────────────────
# Pre-populated config values when a node is first placed on the canvas.

NODE_DEFAULTS: dict[str, dict[str, Any]] = {
    KIND_ROUTE: {
        "path": "/api/items",
        "ops": ["create", "get", "list", "update", "delete"],
    },
    KIND_ROUTE_GROUP: {
        "prefix": "/api",
    },
    KIND_ENTITY: {
        "name": "item",
        "fields": "name:str, description:str?",
    },
    KIND_SERVICE: {
        "name": "item_service",
    },
    KIND_JOB: {
        "name": "process_items",
        "schedule": "0 * * * *",
    },
    KIND_MIDDLEWARE: {
        "name": "cors",
    },
    KIND_FEATURE_FLAG: {
        "name": "new_checkout",
        "enabled": True,
        "description": "",
    },
    KIND_AUTH: {
        "name": "jwt_auth",
        "provider": "jwt",
    },
    KIND_ROLE: {
        "name": "admin",
        "permissions": [],
    },
    KIND_RATE_LIMIT: {
        "name": "api_rate_limit",
        "strategy": "sliding_window",
        "max_requests": 100,
        "window_seconds": 60,
    },
    KIND_CONTRACT: {
        "name": "create_order",
        "direction": "request",
        "fields": "item_id:str, quantity:int",
        "entity": "",
        "enabled": True,
        "description": "",
    },
}

# ── Node colors (Tailwind classes) ────────────────────────────────────

NODE_COLORS: dict[str, str] = {
    KIND_ROUTE: "border-blue-400 bg-blue-50",
    KIND_ROUTE_GROUP: "border-blue-300 bg-blue-50/50",
    KIND_ENTITY: "border-green-400 bg-green-50",
    KIND_SERVICE: "border-purple-400 bg-purple-50",
    KIND_JOB: "border-orange-400 bg-orange-50",
    KIND_MIDDLEWARE: "border-gray-400 bg-gray-50",
    KIND_FEATURE_FLAG: "border-yellow-400 bg-yellow-50",
    KIND_AUTH: "border-red-400 bg-red-50",
    KIND_ROLE: "border-red-300 bg-red-50/50",
    KIND_RATE_LIMIT: "border-amber-400 bg-amber-50",
    KIND_CONTRACT: "border-teal-400 bg-teal-50",
}

# ── Palette categories ────────────────────────────────────────────────
# Groups nodes in the sidebar palette.  Order matters for display.

PALETTE_CATEGORIES: dict[str, list[str]] = {
    "Core": [KIND_ROUTE, KIND_ROUTE_GROUP, KIND_ENTITY],
    "Features": [KIND_FEATURE_FLAG],
    "Security & Policy": [KIND_AUTH, KIND_ROLE, KIND_RATE_LIMIT],
    "Data": [KIND_CONTRACT],
    "Infrastructure": [KIND_SERVICE, KIND_JOB, KIND_MIDDLEWARE],
}

__all__ = [
    "ALLOWED_EDGES",
    "EDGE_KIND_MAP",
    "KIND_AUTH",
    "KIND_CONTRACT",
    "KIND_ENTITY",
    "KIND_FEATURE_FLAG",
    "KIND_JOB",
    "KIND_MIDDLEWARE",
    "KIND_RATE_LIMIT",
    "KIND_ROLE",
    "KIND_ROUTE",
    "KIND_ROUTE_GROUP",
    "KIND_SERVICE",
    "KNOWN_KINDS",
    "NODE_COLORS",
    "NODE_DEFAULTS",
    "NODE_PORTS",
    "PALETTE_CATEGORIES",
    "PORT_COMPATIBILITY",
    "PORT_TYPES",
    "PORT_TYPE_CONFIG_REF",
    "PORT_TYPE_DATA_FLOW",
    "PORT_TYPE_ENTITY_REF",
]
