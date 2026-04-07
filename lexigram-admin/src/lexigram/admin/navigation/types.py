"""Navigation type definitions for admin sidebar construction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NavItem:
    """Navigation item."""

    name: str
    label: str
    url: str
    icon: str | None = None
    badge: str | None = None
    badge_variant: str = "primary"
    active: bool = False
    external: bool = False

    children: list[NavItem] | None = None

    resource_name: str | None = None
    permission: str | None = None


@dataclass
class NavGroup:
    """Navigation group containing multiple items."""

    name: str
    label: str
    icon: str | None = None
    order: int = 0
    collapsible: bool = True
    collapsed: bool = False

    items: list[NavItem] = field(default_factory=list)

    permission: str | None = None
    feature_flag: str | None = None


@dataclass
class SidebarNavItem:
    """Normalized sidebar navigation item.

    Converts ``NavigationContribution`` and resource nav entries into one
    shell-ready shape consumed by ``AdminShell._prepare_navigation()``.
    """

    label: str
    href: str
    icon: str | None = None
    badge: str | None = None
    active: bool = False
    is_group: bool = False
    permission: str | None = None
    feature: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        """Convert to dict for backward-compatible shell consumption."""
        d: dict[str, str | bool | None] = {
            "label": self.label,
            "href": self.href,
            "icon": self.icon,
            "badge": self.badge,
            "active": self.active,
        }
        if self.is_group:
            d["is_group"] = True
        if self.permission:
            d["permission"] = self.permission
        if self.feature:
            d["feature"] = self.feature
        return d


@dataclass
class NavigationConfig:
    """Configuration for navigation assembly."""

    prefix: str = "/admin"

    groups: dict[str, NavGroup] = field(default_factory=dict)

    default_icons: dict[str, str] = field(
        default_factory=lambda: {
            "users": "users",
            "products": "cube",
            "orders": "shopping-cart",
            "settings": "cog",
            "reports": "chart-bar",
            "logs": "document-text",
        },
    )

    show_counts: bool = False


__all__ = ["NavGroup", "NavItem", "NavigationConfig", "SidebarNavItem"]
