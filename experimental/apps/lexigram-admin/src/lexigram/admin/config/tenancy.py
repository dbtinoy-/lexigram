"""Multi-tenancy configuration."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class TenancyConfig(DomainModel):
    """Multi-tenancy configuration for admin.

    Controls tenant resolution, data isolation, and route scoping.

    Attributes:
        enabled: Enable multi-tenancy support.
        tenant_field: Field name used for tenant data filtering (default ``"tenant_id"``).
        header_name: HTTP header name for tenant ID resolution (default ``"x-tenant-id"``).
        cookie_name: Cookie name for tenant ID resolution (default ``"admin_tenant"``).
        default_tenant_id: Fallback tenant ID when none can be resolved.
        route_prefix_template: If set (e.g. ``"{tenant}"``), routes are prefixed
            with the resolved tenant ID. Empty means no route prefix.
    """

    enabled: bool = Field(default=False)
    tenant_field: str = Field(default="tenant_id")
    header_name: str = Field(default="x-tenant-id")
    cookie_name: str = Field(default="admin_tenant")
    default_tenant_id: str = Field(default="")
    route_prefix_template: str = Field(default="")

    model_config = {"extra": "forbid"}
