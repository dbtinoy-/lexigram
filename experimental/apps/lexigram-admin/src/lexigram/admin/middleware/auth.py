"""Authentication middleware for Lexigram Admin.

This middleware integrates with Lexigram's DI container to provide
request-scoped user authentication and authorization.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.requests import Request as StarletteRequest
from starlette.types import ASGIApp, Receive, Scope, Send

from lexigram.admin.auth.models import GUEST_USER
from lexigram.admin.auth.store.base import AbstractAdminUserStore
from lexigram.contracts import AuthenticatedUserProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.primitives import clock

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import AdminSessionServiceProtocol

logger = get_logger(__name__)


@inject
class AdminAuthMiddleware:
    """Pure ASGI middleware for admin authentication and authorization.

    10x faster than BaseHTTPMiddleware - no task creation overhead.

    This middleware:
    1. Checks if user is authenticated (via session/JWT)
    2. Loads AdminUser from session or creates guest user
    3. Injects AdminUser into DI request scope
    4. Optionally redirects unauthenticated users to login

    The injected AdminUser is then available to all controllers
    via dependency injection.
    """

    def __init__(
        self,
        app: ASGIApp,
        user_store: AbstractAdminUserStore | None = None,
        session_service: AdminSessionServiceProtocol | None = None,
        require_auth: bool = False,
        excluded_paths: list[str] | None = None,
    ):
        """Initialize auth middleware.

        Args:
            app: ASGI application
            user_store: AbstractAdminUserStore for loading users
            session_service: AdminSessionServiceProtocol for TTL enforcement
            require_auth: If True, redirect unauthenticated users
            excluded_paths: Paths that don't require authentication
        """
        self.app = app
        self.user_store = user_store
        self._session_service = session_service
        self.require_auth = require_auth
        self.excluded_paths = excluded_paths or []

    def _is_path_excluded(self, path: str) -> bool:
        """Check if path is excluded from auth requirements.

        Args:
            path: Request path to check

        Returns:
            True if path is excluded, False otherwise
        """
        for pattern in self.excluded_paths:
            if pattern.endswith("*"):
                # Wildcard matching
                prefix = pattern[:-1]
                if path.startswith(prefix):
                    return True
            elif path == pattern:
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pure ASGI middleware implementation."""

        if scope["type"] != "http":
            # Pass through non-HTTP requests
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check if path is excluded
        if self._is_path_excluded(path):
            await self.app(scope, receive, send)
            return

        # Build request for store access
        request = StarletteRequest(scope, receive)

        # Resolve tenant
        if hasattr(request.state, "tenant_id"):
            pass

        # Load user from session
        user = await self._load_user(request)

        # Check if authentication is required
        if self.require_auth and (
            user is None or getattr(user, "user_id", "guest") == "guest"
        ):
            from starlette.exceptions import HTTPException

            raise HTTPException(status_code=401, detail="Unauthorized")

        # Store user in scope for access by other middleware/controllers
        scope["user"] = user

        # Also store in scope state (becomes request.state)
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["user"] = user

        # Continue with request
        try:
            await self.app(scope, receive, send)
        finally:
            pass

    async def _load_user(self, request: Request) -> AuthenticatedUserProtocol | None:
        """Load user from request session or return guest user.

        Validates via AdminSessionService (which enforces idle + absolute TTL)
        when both a session_id and session_service are available. Falls back
        to direct user_store lookup for backward compatibility with sessions
        created before the session_id was stored.

        Args:
            request: The incoming request

        Returns:
            AdminUser instance (or GUEST_USER if not authenticated)
        """
        # Canonical admin auth path: signed Starlette session cookie managed by
        # SessionMiddleware + AuthController.
        try:
            if "session" not in request.scope:
                return GUEST_USER

            # ── Session-service path (enforces TTL) ────────────────────
            session_id = request.session.get("session_id")
            if self._session_service is not None:
                if not session_id:
                    # Service-bound deployment without a service-managed
                    # session: never consult the legacy fallback.
                    return GUEST_USER
                session_data = await self._session_service.get_session(session_id)
                if session_data is None:
                    # Session expired or revoked — clear cookie
                    request.session.clear()
                    logger.debug("session.expired_or_revoked", session_id=session_id)
                    return GUEST_USER

                admin_id = session_data.get("admin_id")
                if admin_id is None:
                    request.session.clear()
                    return GUEST_USER

                user = (
                    await self.user_store.get_by_id(admin_id)
                    if self.user_store
                    else None
                )
                if user is None or not user.is_active:
                    await self._session_service.revoke_session(session_id)
                    request.session.clear()
                    return GUEST_USER

                logger.debug(
                    "Successfully loaded user %s from session (TTL-validated)",
                    user.user_id,
                )
                return user

            # ── Legacy fallback (no session_service / no session_id) ───
            user_id = request.session.get("admin_user_id")
            if user_id:
                expires_at_raw = request.session.get("admin_session_expires_at")
                if expires_at_raw is None:
                    request.session.clear()
                    return GUEST_USER
                try:
                    expires_at = datetime.fromisoformat(expires_at_raw)
                except ValueError:
                    request.session.clear()
                    return GUEST_USER
                if expires_at.tzinfo is None or clock.now() >= expires_at:
                    request.session.clear()
                    return GUEST_USER
                user_store = self.user_store
                user = await user_store.get_by_id(user_id) if user_store else None
                if user and user.is_active:
                    logger.debug(
                        "Successfully loaded user %s from request.session",
                        user.user_id,
                    )
                    return user
        except (RuntimeError, ValueError, OSError, AssertionError) as e:
            logger.debug("Failed to load user from request.session: %s", e)

        return GUEST_USER


def current_user(request: Request | None = None) -> AuthenticatedUserProtocol | None:
    """Get the current authenticated user from request scope.

    This is a helper function that can be used in controllers
    when DI injection is not available.

    Args:
        request: Request object (optional, will try to get from DI scope)

    Returns:
        The current User or GUEST_USER

    Example:
        ```python
        @get("/admin/profile")
        async def profile(request: Request):
            user = current_user(request)
            return {"username": user.name}
        ```
    """
    # Try to get from request state first
    if request and hasattr(request.state, "user"):
        return request.state.user

    return GUEST_USER
