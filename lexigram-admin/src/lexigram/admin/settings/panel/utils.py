"""Shared utility functions for the settings panel."""

from __future__ import annotations

from typing import Any


def map_config_node_type(node: Any) -> str:
    """Map a ConfigNode class name to a SettingDefinition storage type string.

    Args:
        node: Any object whose class name follows the ``*Node`` convention.

    Returns:
        Lowercase type string (``"string"``, ``"int"``, ``"bool"``,
        ``"enum"``, or ``"secret"``).
    """
    _type_map: dict[str, str] = {
        "StringNode": "string",
        "IntNode": "int",
        "BooleanNode": "bool",
        "EnumNode": "enum",
        "SecretNode": "secret",
    }
    return _type_map.get(node.__class__.__name__, "string")


__all__ = ["map_config_node_type"]
