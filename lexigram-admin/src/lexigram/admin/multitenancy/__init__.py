"""Multi-tenancy support for lexigram-admin.

Delegates to ``lexigram-tenancy`` when installed; falls back to the
built-in in-memory implementation otherwise.
"""

from __future__ import annotations

from lexigram.admin.multitenancy.adapter import (
    TenantProviderRegistry,
    resolve_tenant_id,
)
from lexigram.admin.multitenancy.data_source import TenantScopedDataSource
from lexigram.admin.multitenancy.models import TenantConfig, TenantNotFoundError

__all__ = [
    "TenantConfig",
    "TenantNotFoundError",
    "TenantProviderRegistry",
    "TenantScopedDataSource",
    "resolve_tenant_id",
]
