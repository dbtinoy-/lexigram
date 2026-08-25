"""Value types for admin DataTable filters: presets and definitions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class FilterPreset:
    """Saved filter configuration."""

    name: str
    filters: dict[str, Any]
    user_id: int | None = None
    is_default: bool = False
    is_shared: bool = False
    created_at: str | None = None


@dataclass
class FilterDefinition:
    """Definition of a filter field using a concrete filter instance."""

    field: str
    filter: Any | None = None
    label: str | None = None
    default_value: Any = None
    validator: Callable[[Any], bool | Awaitable[bool]] | None = None
    required: bool = False
