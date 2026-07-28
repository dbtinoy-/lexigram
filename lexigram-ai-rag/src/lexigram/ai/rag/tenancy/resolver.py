"""Tenant collection resolver for the RAG pipeline.

Reuses the ``TenantCollectionResolver`` protocol from
``lexigram.contracts.data.vector.tenancy``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemplatedTenantCollectionResolver:
    """Resolves a tenant-scoped collection name via string template.

    The template supports ``{logical}`` and ``{tenant}`` placeholders.
    Defaults to ``"{logical}_t_{tenant}"``.
    """

    template: str = "{logical}_t_{tenant}"

    def resolve(self, logical_name: str, tenant_id: str) -> str:
        """Resolve *logical_name* to a tenant-specific collection name."""
        return self.template.format(logical=logical_name, tenant=tenant_id)


__all__ = ["TemplatedTenantCollectionResolver"]
