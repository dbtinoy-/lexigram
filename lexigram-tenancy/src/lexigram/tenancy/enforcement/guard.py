"""Route-level tenant enforcement guard."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.tenancy.types import TenantStatus
from lexigram.primitives.context import TENANT_ID, Context


class TenantGuard:
    """Route-level guard that enforces tenant context presence.

    Applied via ``@use_guards(TenantGuard)`` on controllers or individual
    routes.  Returns ``False`` (triggering a 403 response) if no active
    tenant is present in the current request scope.

    The guard reads ``TENANT_ID`` from the shared context AND verifies the
    tenant stored in ``scope["state"]["tenant"]`` has ``ACTIVE`` status.

    Usage::

        @use_guards(TenantGuard)
        class TenantAwareController: ...
    """

    def __init__(self, ctx: Context) -> None:
        """Initialise the guard with the shared context.

        Args:
            ctx: The shared :class:`~lexigram.primitives.context.Context`.
        """
        self._ctx = ctx

    async def can_activate(self, execution_context: Any) -> bool:
        """Check whether the current request may proceed.

        Args:
            execution_context: The framework execution context, which must
                expose ``execution_context.request.scope`` for tenant state
                lookup.

        Returns:
            ``True`` if a valid, active tenant is in context; ``False``
            otherwise (results in 403 Forbidden).
        """
        tenant_id = self._ctx.get(TENANT_ID)
        if not tenant_id:
            return False
        try:
            scope = execution_context.request.scope
            tenant = scope.get("state", {}).get("tenant")
        except AttributeError:
            return False
        if not tenant:
            return False
        return tenant.status == TenantStatus.ACTIVE


__all__ = ["TenantGuard"]
