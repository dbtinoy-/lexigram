"""Route-level auth guards and decorators for lexigram-admin.

Permission/role/composite guards plus the ``require_auth`` and
``csrf_protect`` decorators. The HTTP middleware lives in ``guards``.
"""

from __future__ import annotations

from functools import wraps
import hmac
from typing import TYPE_CHECKING, Any

from starlette.requests import Request

from lexigram.admin.auth.permissions import PermissionSet, get_user_permissions
from lexigram.admin.exceptions import ErrorCode, PermissionDeniedError
from lexigram.contracts import AuthorizerProtocol
from lexigram.contracts.web import RequestProtocol
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)


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

        if not expected_token:
            # Fail closed: a session without CSRF state cannot authorize
            # state-changing requests.
            logger.warning("csrf_rejected_no_session_token")
            raise PermissionDeniedError(
                message="Missing CSRF session state",
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )

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

        if not submitted_token or not hmac.compare_digest(
            submitted_token, expected_token
        ):
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
