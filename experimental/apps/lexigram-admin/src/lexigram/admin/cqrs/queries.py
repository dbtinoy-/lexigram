"""Standard admin query types for the CQRS layer.

Queries are read-only operations; they never mutate state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class AdminQuery:
    """Base class for all admin queries."""

    query_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None

    @property
    def name(self) -> str:
        """Return the query class name."""
        return self.__class__.__name__


# ========== User Queries ==========


@dataclass
class GetAdminUser(AdminQuery):
    """Query a single admin user by ID."""

    user_id: str = ""


@dataclass
class ListAdminUsers(AdminQuery):
    """Query a paginated list of admin users."""

    page: int = 1
    page_size: int = 20
    search: str | None = None
    role_filter: str | None = None


# ========== Resource Queries ==========


@dataclass
class GetResource(AdminQuery):
    """Query a single resource record."""

    resource_type: str = ""
    resource_id: Any = None


@dataclass
class ListResources(AdminQuery):
    """Query a paginated list of resource records."""

    resource_type: str = ""
    page: int = 1
    page_size: int = 20
    filters: dict[str, Any] = field(default_factory=dict)
    order_by: str | None = None
    order_dir: str = "asc"


@dataclass
class SearchResources(AdminQuery):
    """Full-text search across a resource type."""

    resource_type: str = ""
    query: str = ""
    page: int = 1
    page_size: int = 20


# ========== Dashboard Queries ==========


@dataclass
class GetDashboardStats(AdminQuery):
    """Query summary statistics for the admin dashboard."""

    resource_types: list[str] = field(default_factory=list)


@dataclass
class GetAuditLog(AdminQuery):
    """Query recent audit log entries."""

    page: int = 1
    page_size: int = 50
    resource_type: str | None = None
    action: str | None = None
    actor_id: str | None = None


__all__ = [
    "AdminQuery",
    "GetAdminUser",
    "GetAuditLog",
    "GetDashboardStats",
    "GetResource",
    "ListAdminUsers",
    "ListResources",
    "SearchResources",
]
