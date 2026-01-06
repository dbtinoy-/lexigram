"""Tenant collection resolver implementations."""

from __future__ import annotations


class TemplatedTenantCollectionResolver:
    """Resolve collection names by applying a tenant-aware template.

    The default template is ``"{logical}_t_{tenant}"`` which produces
    names like ``"canon_t_t1"``.

    Usage::

        resolver = TemplatedTenantCollectionResolver()
        resolver.resolve("canon", "t1")  # → "canon_t_t1"
    """

    def __init__(self, template: str = "{logical}_t_{tenant}") -> None:
        self._template = template

    def resolve(self, logical_name: str, tenant_id: str) -> str:
        """Apply the template to produce a tenant-specific name.

        Args:
            logical_name: Logical collection name.
            tenant_id: Tenant identifier.

        Returns:
            Templated collection name.
        """
        return self._template.format(logical=logical_name, tenant=tenant_id)


__all__ = ["TemplatedTenantCollectionResolver"]
