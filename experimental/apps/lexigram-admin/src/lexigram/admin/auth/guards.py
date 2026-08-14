"""Authentication and authorization guards for lexigram-admin.

Provides middleware and guard utilities for protecting routes.
Integrates with lexigram-auth session management.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.permissions import PermissionSet, get_user_permissions
from lexigram.admin.exceptions import ErrorCode, PermissionDeniedError
from lexigram.contracts import (
    AuthorizerProtocol,
    AuthProviderProtocol,
)
from lexigram.contracts.web import RequestProtocol, ResponseProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.serialization.backends import json as json_backend

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)


@dataclass
class GuardConfig:
    """Configuration for authentication guards."""

    login_url: str = "/admin/login"
    logout_url: str = "/admin/logout"
    exempt_paths: tuple[str, ...] = (
        "/admin/login",
        "/admin/static",
        "/admin/health",
        # Standalone pre-session flows (own CSRF + guest handling):
        "/admin/setup",
        "/admin/verify-email",
        "/admin/password-reset",
    )
    # Whether to accept Authorization: Bearer <token> for admin APIs.
    # Default: False to enforce strict cookie-based admin sessions.
    allow_bearer_tokens: bool = False
    htmx_redirect_header: str = "HX-Redirect"


@inject
class AuthGuardMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces authentication on admin routes.

    Checks for valid session and loads user into request.state.
    Redirects unauthenticated requests to login page.

    For HTMX requests, returns HX-Redirect header instead of 302.
    """

    def __init__(
        self,
        app: Any,
        auth_provider: AuthProviderProtocol | None = None,
        config: GuardConfig | None = None,
        authorizer: AuthorizerProtocol | None = None,
    ) -> None:
        super().__init__(app)
        self.auth_provider = auth_provider
        self.config = config or GuardConfig()
        self.authorizer = authorizer

    async def dispatch(  # type: ignore[override]
        self,
        request: RequestProtocol,  # type: ignore[override]
        call_next: RequestResponseEndpoint,
    ) -> ResponseProtocol:
        # Skip auth for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)  # type: ignore[return-value, arg-type]

        # Check if user is already loaded by AdminAuthMiddleware
        user = getattr(request.state, "user", None)

        # If not, try to load it (fallback/standalone usage)
        if user is None:
            user = await self._get_authenticated_user(request)

        if not self._is_authenticated(user):
            # If request has Authorization: Bearer, return 401 instead of redirect
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from starlette.responses import JSONResponse

                return JSONResponse(  # type: ignore[return-value]
                    {"authenticated": False, "detail": "Invalid or missing token"},
                    status_code=401,
                )
            return self._redirect_to_login(request)

        # Ensure user and permissions are in state
        request.state.user = user
        if not hasattr(request.state, "permissions"):
            # Use injected authorizer if available
            if self.authorizer:
                try:
                    request.state.permissions = get_user_permissions(
                        user,
                        self.authorizer,
                    )
                except (
                    ConnectionError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                    AttributeError,
                ):
                    # Authorization failed, skip permissions
                    logger.debug(
                        "Could not compute user permissions",
                        exc_info=True,
                    )
                    request.state.permissions = None
            else:
                # No authorizer available, skip permissions
                request.state.permissions = None

        return await call_next(request)  # type: ignore[return-value, arg-type]

    def _is_authenticated(self, user: Any) -> bool:
        """Check if user is traditionally authenticated (not guest)."""
        if user is None:
            return False

        # Check common identity fields
        user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
        if not user_id or user_id == "guest":
            return False

        # Check activity
        return getattr(user, "is_active", True)

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from auth."""
        return any(path.startswith(exempt) for exempt in self.config.exempt_paths)

    async def _get_authenticated_user(self, request: RequestProtocol) -> Any | None:
        """Get authenticated user from signed request session."""
        if "session" in request.scope:  # type: ignore[attr-defined]
            user_id = request.session.get("admin_user_id")  # type: ignore[attr-defined]
            if user_id:
                try:
                    if hasattr(self.auth_provider, "user_store"):
                        return await self.auth_provider.user_store.get_user_by_id(  # type: ignore[union-attr]
                            user_id,
                        )
                    return None
                except (
                    ConnectionError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                    AttributeError,
                ):
                    logger.debug("Session user resolution failed", exc_info=True)

        # Try Authorization header (for API calls)
        # By default, admin routes do NOT accept bearer tokens to keep a strict
        # separation between admin sessions (cookie-based) and application
        # JWTs. This can be enabled explicitly via GuardConfig.allow_bearer_tokens.
        if self.config.allow_bearer_tokens:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    # lexigram-auth uses authenticate_user or verify_token but AuthGuard usually checks tokens too
                    if hasattr(self.auth_provider, "verify_token"):
                        token_result = self.auth_provider.verify_token(token)  # type: ignore[union-attr]
                        if hasattr(token_result, "__await__"):
                            token_result = await token_result
                        # Handle Result[VerifiedToken, ...] (new API)
                        if hasattr(token_result, "is_ok"):
                            if token_result.is_ok():
                                verified = token_result.unwrap()  # type: ignore[union-attr]
                                return (
                                    await self.auth_provider.user_store.get_user_by_id(  # type: ignore[union-attr]
                                        verified.user_id,
                                    )
                                )
                        # Fallback: legacy dict payload (older providers)
                        elif token_result and "sub" in token_result:  # type: ignore[operator]
                            return await self.auth_provider.user_store.get_user_by_id(  # type: ignore[union-attr]
                                token_result["sub"],  # type: ignore[index]
                            )
                    elif self.auth_provider is not None and hasattr(
                        self.auth_provider, "validate_token"
                    ):
                        payload = self.auth_provider.validate_token(token)
                        if hasattr(payload, "__await__"):
                            payload = await payload
                        if (
                            payload
                            and "sub" in payload
                            and self.auth_provider is not None
                        ):
                            user_store = getattr(self.auth_provider, "user_store", None)
                            if user_store is not None:
                                return await user_store.get_user_by_id(
                                    payload["sub"],
                                )
                        return payload
                except (
                    ConnectionError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                    AttributeError,
                ) as e:
                    # Provide richer diagnostic logging so we can see token header issues (e.g., unexpected 'alg')
                    try:
                        header = None
                        try:
                            segment = token.split(".", 1)[0]
                            padded = segment + "=" * (-len(segment) % 4)
                            header = json_backend.loads(
                                base64.urlsafe_b64decode(padded)
                            )
                        except (ValueError, TypeError):
                            header = None
                        logger.warning(
                            "Token validation failed: %s - header=%s",
                            str(e),
                            header,
                            exc_info=True,
                        )
                    except (OSError, ValueError, TypeError) as e:
                        logger.warning("Token validation failed", exc_info=True)
        return None

    def _redirect_to_login(self, request: RequestProtocol) -> ResponseProtocol:
        """Create redirect response to login page."""
        # Build redirect URL with return path
        return_to = request.url.path
        if request.url.query:
            return_to = f"{return_to}?{request.url.query}"

        login_url = f"{self.config.login_url}?next={return_to}"

        # For HTMX requests, use HX-Redirect header
        if request.headers.get("HX-Request"):
            response = Response(status_code=200)
            response.headers[self.config.htmx_redirect_header] = login_url
            return response  # type: ignore[return-value]

        return RedirectResponse(url=login_url, status_code=302)  # type: ignore[return-value]


class PermissionGuard:
    """GuardProtocol that checks permissions on specific routes.

    Usage with @use_guards decorator:
        class UserController(Controller):
            @get("/admin/users")
            @use_guards(PermissionGuard("users.list"))
            async def list_users(self, request: Request) -> ...: ...

    Usage as standalone callable:
        guard = PermissionGuard("users.delete")
        result = await guard(request)
        if result.is_err():
            raise result.unwrap_err()
    """

    def __init__(
        self,
        *permissions: str,
        require_all: bool = False,
        message: str | None = None,
        authorizer: AuthorizerProtocol | None = None,
    ):
        self.permissions = permissions
        self.require_all = require_all
        self.message = message
        self._authorizer = authorizer

    async def __call__(
        self, request: RequestProtocol
    ) -> Result[None, PermissionDeniedError]:
        """Check permissions. Returns Ok(None) on success, Err(PermissionDeniedError) on denial."""
        user = getattr(request.state, "user", None)

        if user is None:
            return Err(PermissionDeniedError(message="Authentication required"))

        user_perms: PermissionSet = getattr(request.state, "permissions", None)  # type: ignore[assignment]
        if user_perms is None:
            # Use injected authorizer or fallback to request.state.permissions if already set
            authorizer = self._authorizer
            if authorizer is None:
                # Permissions should have been set by middleware
                return Err(
                    PermissionDeniedError(
                        message="Authorization service unavailable",
                    )
                )
            user_perms = get_user_permissions(user, authorizer)

        if self.require_all:
            if not user_perms.has_all(*self.permissions):
                missing = list(
                    filter(lambda p: not user_perms.has(p), self.permissions),
                )
                return Err(
                    PermissionDeniedError(
                        message=self.message
                        or f"Missing permissions: {', '.join(missing)}",
                        required_permission=str(self.permissions),
                    )
                )
        elif not user_perms.has_any(*self.permissions):
            return Err(
                PermissionDeniedError(
                    message=self.message
                    or f"Requires permission: {' or '.join(self.permissions)}",
                    required_permission=str(self.permissions),
                )
            )
        return Ok(None)

    def __matmul__(self, func: Callable) -> Callable:
        """Allow usage as @guard decorator via @ operator."""
        return self.wrap(func)

    def wrap(
        self,
        func: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        """Wrap a function with permission check.

        Raises PermissionDeniedError if the guard check fails.
        """

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs) -> Any:
            result = await self(request)  # type: ignore[arg-type]
            if result.is_err():
                raise result.unwrap_err()
            return await func(request, *args, **kwargs)

        return wrapper


class RoleGuard:
    """GuardProtocol that checks roles on specific routes."""

    def __init__(
        self,
        *roles: str,
        require_all: bool = False,
        message: str | None = None,
    ):
        self.roles = roles
        self.require_all = require_all
        self.message = message

    async def __call__(
        self, request: RequestProtocol
    ) -> Result[None, PermissionDeniedError]:
        """Check roles. Returns Ok(None) on success, Err(PermissionDeniedError) on denial."""
        user = getattr(request.state, "user", None)

        if user is None:
            return Err(PermissionDeniedError(message="Authentication required"))

        user_roles = set(getattr(user, "roles", []) or [])

        if self.require_all:
            if not all(r in user_roles for r in self.roles):
                missing = list(filter(lambda r: r not in user_roles, self.roles))
                return Err(
                    PermissionDeniedError(
                        message=self.message
                        or f"Requires all roles: {', '.join(missing)}",
                    )
                )
        elif not user_roles.intersection(self.roles):
            return Err(
                PermissionDeniedError(
                    message=self.message or f"Requires role: {' or '.join(self.roles)}",
                )
            )
        return Ok(None)


def require_auth(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Simple decorator to require authentication.

    Just checks that user exists in request.state.
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs) -> Any:
        user = getattr(request.state, "user", None)
        if user is None:
            raise PermissionDeniedError(message="Authentication required")
        return await func(request, *args, **kwargs)

    return wrapper


def csrf_protect(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Decorator to require valid CSRF token for state-changing operations.

    Checks for CSRF token in:
    1. X-CSRF-Token header
    2. csrf_token form field

    HTMX requests automatically include the token via hx-headers.
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs) -> Any:
        # Skip for safe methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await func(request, *args, **kwargs)

        # Get expected token from session
        session = getattr(request.state, "session", None)
        expected_token = getattr(session, "csrf_token", None) if session else None

        if expected_token is None:
            # No CSRF protection configured
            logger.warning("CSRF protection skipped - no token in session")
            return await func(request, *args, **kwargs)

        # Get submitted token
        submitted_token = request.headers.get("X-CSRF-Token")

        if not submitted_token:
            # Try form data
            try:
                form = request.scope.get("admin_form_data")
                if form is None:
                    form = await request.form()
                submitted_token = form.get("csrf_token")  # type: ignore[assignment]
            except (
                ConnectionError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ):
                pass

        if not submitted_token or submitted_token != expected_token:
            raise PermissionDeniedError(
                message="Invalid or missing CSRF token",
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )

        return await func(request, *args, **kwargs)

    return wrapper


class CompositeGuard:
    """Combine multiple guards with AND/OR logic.

    Usage:
        guard = CompositeGuard(
            PermissionGuard("users.list"),
            RoleGuard("admin"),
            logic="or"  # User needs permission OR role
        )
    """

    def __init__(
        self,
        *guards: PermissionGuard | RoleGuard,
        logic: str = "and",  # "and" or "or"
    ):
        self.guards = guards
        self.logic = logic

    async def __call__(
        self, request: RequestProtocol
    ) -> Result[None, PermissionDeniedError]:
        """Execute guards based on logic.

        Returns Ok(None) when guard(s) pass. Returns Err(PermissionDeniedError)
        on denial. For "and" logic, the first failure short-circuits. For "or"
        logic, the last failure is returned if all guards deny.
        """
        if self.logic == "and":
            # All guards must pass — short-circuit on first failure
            for guard in self.guards:
                result = await guard(request)
                if result.is_err():
                    return result
            return Ok(None)
        # At least one guard must pass
        last_failure: Result[None, PermissionDeniedError] = Err(
            PermissionDeniedError(message="All guards denied access")
        )
        for guard in self.guards:
            result = await guard(request)
            if result.is_ok():
                return Ok(None)
            last_failure = result
        return last_failure
