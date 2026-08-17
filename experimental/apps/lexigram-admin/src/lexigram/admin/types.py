"""Type definitions for lexigram admin."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict


@dataclass
class ExtensionConfig:
    """Configuration for an admin extension."""

    enabled: bool = True
    nav_label: str | None = None
    nav_icon: str | None = None
    nav_location: str = "sidebar"  # sidebar | system-menu | user-menu | hidden
    nav_order: int = 100
    nav_permission: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


class AdminStatus(str, Enum):
    """Status of admin operations."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class AdminUser:
    """Admin user representation."""

    id: str
    username: str
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


class NavigationItem(TypedDict, total=False):
    """A single navigation item in the admin sidebar."""

    label: str
    url: str
    icon: str
    group: str
    permission: str
    children: list[NavigationItem]
    active: bool


class MiddlewareOptions(TypedDict, total=False):
    """Options passed to admin middleware registration."""

    debug: bool
    timeout: float
    exclude_paths: list[str]


class TemplateContext(TypedDict, total=False):
    """Template rendering context for admin pages."""

    title: str
    user: object
    nav_items: list[NavigationItem]
    breadcrumbs: list[dict]
    request: object
    content: str
    error: str | None
    flash: str | None


__all__ = [
    "AdminStatus",
    "AdminUser",
    "ExtensionConfig",
    "MiddlewareOptions",
    "NavigationItem",
    "TemplateContext",
]
