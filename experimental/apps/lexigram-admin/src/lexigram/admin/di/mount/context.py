"""Shared mutable context for the admin mount pipeline.

Collects state produced by one mount phase and consumed by later phases so
that the individual mount steps stay decoupled from each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MountContext:
    """Cross-phase state produced while mounting the admin panel."""

    resources: dict[str, Any] = field(default_factory=dict)
    controllers: list[Any] = field(default_factory=list)
    middlewares: list[tuple[type, dict[str, Any]]] = field(default_factory=list)
    contributors: list[Any] = field(default_factory=list)
    settings_service: Any | None = None
    contributor_registry: Any | None = None
    cluster_registry: Any | None = None
    nav_builder: Any | None = None
    router: Any | None = None
    admin_app: Any | None = None
