"""Tenant data models — TenantConfig and TenantNotFoundError."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantConfig:
    """Configuration for a single tenant.

    Attributes:
        tenant_id: Unique slug identifier (e.g. ``"acme"``).
        name: Human-readable display name.
        domain: Optional custom domain for subdomain-based resolution.
        logo_url: Optional logo URL shown in the admin UI switcher.
        primary_color: Optional hex colour override for the admin theme.
        active: Whether this tenant is currently active.
        metadata: Arbitrary extra metadata.
    """

    tenant_id: str
    name: str
    domain: str = ""
    logo_url: str = ""
    primary_color: str = ""
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError("TenantConfig.tenant_id must not be empty")
        if not self.name:
            raise ValueError("TenantConfig.name must not be empty")


class TenantNotFoundError(KeyError):
    """Raised when a tenant is not found in the registry."""

    _code: str = "LEX_ERR_ADMIN_030"


__all__ = [
    "TenantConfig",
    "TenantNotFoundError",
]
