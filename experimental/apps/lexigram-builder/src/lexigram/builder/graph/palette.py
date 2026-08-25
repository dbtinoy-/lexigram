"""Node-kind palette: kinds, field types, ops, edge rules."""

from __future__ import annotations

import keyword

KIND_APP_SETTINGS = "app_settings"
KIND_ENTITY = "entity"
KIND_ROUTE = "route"

KNOWN_KINDS: frozenset[str] = frozenset({KIND_APP_SETTINGS, KIND_ENTITY, KIND_ROUTE})

FIELD_TYPES: frozenset[str] = frozenset(
    {"str", "int", "float", "bool", "datetime", "uuid"}
)

ENTITY_OPS: frozenset[str] = frozenset({"create", "get", "list", "update", "delete"})

DB_PRESETS: frozenset[str] = frozenset({"sqlite", "postgres"})

ALLOWED_EDGES: frozenset[tuple[str, str]] = frozenset({(KIND_ROUTE, KIND_ENTITY)})

PORT_MIN = 1024
PORT_MAX = 65535


def is_known_kind(kind: str) -> bool:
    """Return True when *kind* is in the palette."""
    return kind in KNOWN_KINDS


def is_snake_case_identifier(name: str) -> bool:
    """Return True for lowercase snake_case Python identifiers.

    Rejects CamelCase, leading underscores/digits, keywords, and any name
    that is not a valid identifier.
    """
    if not name or not name.isidentifier() or keyword.iskeyword(name):
        return False
    if not name[0].isalpha():
        return False
    return name == name.lower()


def is_valid_port(port: int) -> bool:
    """Return True when *port* fits the allowed bind range."""
    return PORT_MIN <= port <= PORT_MAX
