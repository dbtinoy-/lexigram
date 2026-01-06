"""Starlette middleware for RBAC."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from lexigram.admin.rbac.service import PermissionService
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class RBACMiddleware(BaseHTTPMiddleware):
    """Middleware that attaches user permissions to the request context."""

    def __init__(
        self,
        app: Any,
        user_provider: Callable[[Request], Any] | None = None,
        role_extractor: Callable[[Any], set[str]] | None = None,
        permission_service: PermissionService | None = None,
    ):
        super().__init__(app)
        self.user_provider = user_provider or (lambda r: getattr(r.state, "user", None))
        self.role_extractor = role_extractor or (lambda u: set(getattr(u, "roles", [])))
        self._permission_service = permission_service

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 1. Resolve User
        user = self.user_provider(request)

        if user:
            # 2. Attach injected permissions service to request state
            request.state.permissions = self._permission_service

            # 3. Optional: Pre-fetch or cache user roles in request state
            roles = self.role_extractor(user)
            request.state.user_roles = roles

            logger.debug(
                "RBAC: User %s has roles %s",
                getattr(user, "id", "unknown"),
                roles,
            )

        return await call_next(request)
