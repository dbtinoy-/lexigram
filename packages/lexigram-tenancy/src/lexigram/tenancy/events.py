"""Tenancy domain events — re-exports from contracts."""

from __future__ import annotations

from lexigram.contracts.tenancy.events import (
    TenantActivated,
    TenantConfigChanged,
    TenantDeactivated,
    TenantProvisioned,
    TenantSuspended,
)

__all__ = [
    "TenantActivated",
    "TenantConfigChanged",
    "TenantDeactivated",
    "TenantProvisioned",
    "TenantSuspended",
]
