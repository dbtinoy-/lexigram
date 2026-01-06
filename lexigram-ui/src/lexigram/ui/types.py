"""UI package common types and dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NavItem:
    """A single item in a navigation component."""

    label: str
    url: str
    icon: str | None = None
    active: bool = False
    children: list[NavItem] = field(default_factory=list)


@dataclass
class Breadcrumb:
    """A breadcrumb trail item."""

    label: str
    url: str | None = None
    active: bool = False
