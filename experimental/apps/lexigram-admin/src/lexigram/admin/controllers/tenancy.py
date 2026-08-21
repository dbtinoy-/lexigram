"""Tenant-switching controller for the admin panel."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.protocols import AdminAuditLogServiceProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminConfig
from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.contracts.web import post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class TenancyController:
    """Handles superadmin tenant-switching.

    CSRF is validated by the global ``AdminCsrfMiddleware`` already applied
    to every admin POST route — this controller does not duplicate that
    check.
    """

    prefix = ""

    def __init__(
        self,
        config: AdminConfig,
        registry: TenantProviderRegistry | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
    ) -> None:
        self._config = config
        self._registry = registry
        self._audit_service = audit_service

    @post("/set-tenant")
    async def set_tenant(self, request: Request) -> Response:
        """Switch the active tenant for a superadmin session."""
        if not self._config.tenancy.enabled or self._registry is None:
            return Response(status_code=404)

        user = getattr(request.state, "user", None)
        if not user or not is_super_admin(user, self._config.rbac.super_admin_role):
            return Response(content="Forbidden", status_code=403)

        data = request.scope.get("admin_form_data")
        if data is None:
            data = await request.form()
        tenant_id = str(data.get("tenant_id", "")).strip()

        tenant = await self._registry.get(tenant_id) if tenant_id else None
        if tenant is None:
            return Response(content="Unknown tenant", status_code=400)

        previous_tenant_id = getattr(request.state, "tenant_id", None) or "default"

        redirect_to = request.headers.get("referer") or "/admin/"
        response = RedirectResponse(url=redirect_to, status_code=303)
        response.set_cookie(
            self._config.tenancy.cookie_name,
            tenant.tenant_id,
            httponly=True,
            samesite="lax",
        )

        await self._audit(
            request,
            from_tenant=previous_tenant_id,
            to_tenant=tenant.tenant_id,
        )

        return response

    async def _audit(self, request: Request, **metadata: Any) -> None:
        """Log a TENANT_SWITCHED event, best-effort."""
        if not self._audit_service:
            return
        try:
            client = getattr(request, "client", None)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.TENANT_SWITCHED,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=True,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break the switch
            logger.warning("tenancy.audit_failed", **metadata)
