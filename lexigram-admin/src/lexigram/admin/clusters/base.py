"""Cluster dataclass for grouping resources and pages.

.. experimental::
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, kw_only=True)
class Cluster:
    """A grouping of resources and pages with shared label, icon, and permissions.

    Example:
        >>> content = Cluster(
        ...     name="content",
        ...     label="Content",
        ...     icon="document",
        ... )
        >>> users = Cluster(
        ...     name="users",
        ...     label="Users & Access",
        ...     icon="users",
        ... )
    """

    name: str
    label: str
    icon: str | None = None
    order: int = 0
    collapsible: bool = True
    collapsed_by_default: bool = False

    # Populated at registration time
    resources: list[type[Any]] = field(default_factory=list)
    pages: list[type[Any]] = field(default_factory=list)


__all__ = ["Cluster"]
