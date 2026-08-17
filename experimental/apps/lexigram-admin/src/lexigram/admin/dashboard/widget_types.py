from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfigField:
    """Schema field for a configurable widget parameter."""

    name: str
    type: str  # "select" | "number" | "text" | "boolean"
    label: str
    options: list[tuple[str | int, str]] | None = (
        None  # (value, display_label) for select
    )
    default: str | int | bool | float | None = None
    description: str = ""
