"""Pinecone-specific tenant resolver using namespaces instead of name-mangling."""

from __future__ import annotations


class PineconeNamespaceTenantResolver:
    """Resolve collection names without mangling — Pinecone native namespace.

    Pinecone supports per-operation namespaces on a shared index. This
    resolver returns the logical name unchanged so the same index is
    used by all tenants; per-tenant isolation is achieved via Pinecone's
    ``namespace`` parameter (set at query/upsert time, not at index
    creation).

    Usage::

        resolver = PineconeNamespaceTenantResolver()
        resolver.resolve("my_index", "t1")  # → "my_index"
    """

    def resolve(self, logical_name: str, tenant_id: str) -> str:
        """Return the logical name unchanged.

        Args:
            logical_name: Logical collection/index name.
            tenant_id: Tenant identifier (ignored — isolation is via
                Pinecone's ``namespace`` parameter).

        Returns:
            The same *logical_name* unmodified.
        """
        return logical_name


__all__ = ["PineconeNamespaceTenantResolver"]
