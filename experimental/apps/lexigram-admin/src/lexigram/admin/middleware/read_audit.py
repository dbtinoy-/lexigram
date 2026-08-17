"""Optional read-audit middleware — logs GET requests (off by default)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from lexigram.admin.audit.correlation import get_correlation_id
from lexigram.contracts.admin.audit_entry import AuditEntry
from lexigram.contracts.admin.audit_logger import AdminAuditLoggerProtocol


class AdminReadAuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs admin GET requests for compliance auditing.

    Only active when ``read_audit_enabled`` is ``True``. When enabled,
    every GET request matching typical admin resource patterns
    (``/admin/...``) is recorded as a low-verbosity ``AuditEntry``
    with ``outcome="success"`` and no before/after diff.
    """

    def __init__(
        self,
        app: ASGIApp,
        audit_logger: AdminAuditLoggerProtocol,
        read_audit_enabled: bool = False,
        admin_prefix: str = "/admin",
    ) -> None:
        super().__init__(app)
        self._audit_logger = audit_logger
        self._read_audit_enabled = read_audit_enabled
        self._admin_prefix = admin_prefix

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        if not self._read_audit_enabled:
            return response

        if request.method.upper() != "GET":
            return response

        if not request.url.path.startswith(self._admin_prefix):
            return response

        if request.url.path in (
            f"{self._admin_prefix}/login",
            f"{self._admin_prefix}/logout",
            f"{self._admin_prefix}/health",
            f"{self._admin_prefix}/static",
        ):
            return response

        user_id = getattr(request.state, "user", None)
        user_id_str = (
            str(getattr(user_id, "user_id", user_id)) if user_id else "anonymous"
        )

        entry = AuditEntry(
            admin_user_id=user_id_str,
            action="read.list"
            if "/" + request.url.path.split("/")[-1] == ""
            else "read.detail",
            resource_type="admin_page",
            resource_id=request.url.path,
            outcome="success",
            correlation_id=get_correlation_id(),
            request_id=request.headers.get("X-Request-ID"),
            request_ip=request.client.host if request.client else None,
            metadata={"method": "GET", "query": str(request.query_params)},
        )
        await self._audit_logger.write(entry)
        return response


__all__ = ["AdminReadAuditMiddleware"]
