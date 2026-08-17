"""Permission definitions and checks for lexigram-admin.

Integrates with lexigram-auth authorization_service for RBAC.
Provides declarative permission decorators and guard middleware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from lexigram.contracts.auth.guard import AuthorizerProtocol as AuthorizationService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence


class Action(StrEnum):
    """Standard CRUD actions for resources."""

    LIST = "list"
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    BULK_DELETE = "bulk_delete"
    BULK_UPDATE = "bulk_update"

    @classmethod
    def all_actions(cls) -> list[Action]:
        """All standard actions."""
        return list(cls)

    @classmethod
    def read_only(cls) -> list[Action]:
        """Read-only actions."""
        return [cls.LIST, cls.VIEW, cls.EXPORT]

    @classmethod
    def write(cls) -> list[Action]:
        """Write actions."""
        return [cls.CREATE, cls.UPDATE, cls.DELETE, cls.BULK_DELETE, cls.BULK_UPDATE]


@dataclass(frozen=True, slots=True)
class Permission:
    """A single permission definition.

    Permissions follow the pattern: resource.action
    Examples: "users.list", "posts.delete", "admin.settings"
    """

    resource: str
    action: str

    def __str__(self) -> str:
        return f"{self.resource}.{self.action}"

    @classmethod
    def from_string(cls, s: str) -> Permission:
        """Parse from "resource.action" string."""
        parts = s.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {s}")
        return cls(resource=parts[0], action=parts[1])

    @classmethod
    def for_resource(
        cls,
        resource: str,
        actions: Sequence[Action] | None = None,
    ) -> list[Permission]:
        """Generate permissions for a resource."""
        actions = actions or Action.all_actions()
        return [cls(resource=resource, action=a.value) for a in actions]


@dataclass(slots=True)
class PermissionSet:
    """Collection of permissions with set operations."""

    permissions: set[str] = field(default_factory=set)

    def add(self, *perms: str | Permission) -> PermissionSet:
        """Add permissions."""
        for p in perms:
            self.permissions.add(str(p))
        return self

    def remove(self, *perms: str | Permission) -> PermissionSet:
        """Remove permissions."""
        for p in perms:
            self.permissions.discard(str(p))
        return self

    def has(self, perm: str | Permission) -> bool:
        """Check if permission exists."""
        perm_str = str(perm)
        # Check exact match
        if perm_str in self.permissions:
            return True
        # Check wildcard patterns
        if "*" in self.permissions:
            return True
        # Check resource wildcard (e.g., "users.*")
        parts = perm_str.split(".", 1)
        return bool(len(parts) == 2 and f"{parts[0]}.*" in self.permissions)

    def has_any(self, *perms: str | Permission) -> bool:
        """Check if any permission exists."""
        return any(self.has(p) for p in perms)

    def has_all(self, *perms: str | Permission) -> bool:
        """Check if all permissions exist."""
        return all(self.has(p) for p in perms)

    def __contains__(self, perm: str | Permission) -> bool:
        return self.has(perm)

    def __iter__(self) -> Any:
        return iter(self.permissions)

    def __len__(self) -> int:
        return len(self.permissions)

    @classmethod
    def from_roles(
        cls,
        roles: Sequence[str],
        authorization_service: AuthorizationService,
    ) -> PermissionSet:
        """Build permission set from role names using authorization_service."""
        perms = set()
        for role in roles:
            role_perms = authorization_service.get_role_permissions(role)  # type: ignore[attr-defined]
            perms.update(role_perms)
        return cls(permissions=perms)


@runtime_checkable
class HasPermissions(Protocol):
    """Protocol for objects that have permissions."""

    @property
    def permissions(self) -> Sequence[str]:
        """Get list of permission strings."""
        ...

    @property
    def roles(self) -> Sequence[str]:
        """Get list of role names."""
        ...


def get_user_permissions(
    user: Any,
    authorization_service: AuthorizationService,
) -> PermissionSet:
    """Extract permissions from a user object.

    Handles both direct permissions and role-based permissions.
    """
    perms = PermissionSet()

    # Direct permissions
    direct = getattr(user, "permissions", []) or []
    perms.add(*direct)

    # Role-based permissions
    roles = getattr(user, "roles", []) or []
    for role in roles:
        role_perms = authorization_service.get_role_permissions(role)  # type: ignore[attr-defined]
        perms.add(*role_perms)

    return perms


P = ParamSpec("P")
R = TypeVar("R")


def _get_permission_set(request: Any) -> PermissionSet | None:
    """Extract PermissionSet from request state."""
    state = getattr(request, "state", None)
    if state is None:
        return None
    ps = getattr(state, "permissions", None)
    if isinstance(ps, PermissionSet):
        return ps
    return None


def require_permission(*permissions: str | Permission) -> Any:
    """Decorator to require any of the listed permissions on a handler.

    Checks ``request.state.permissions`` (a PermissionSet). If not present
    or the required permission is missing, raises PermissionDeniedError.

    Usage:
        @require_permission("users.list")
        async def list_users(request): ...

        @require_permission("posts.create", "posts.update")
        async def manage_posts(request): ...
    """
    perm_strings = list(map(str, permissions))

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = args[0] if args else kwargs.get("request")
            if request is None:
                raise ValueError("No request object found for permission check")

            ps = _get_permission_set(request)
            if ps is None:
                from lexigram.admin.exceptions import PermissionDeniedError

                raise PermissionDeniedError(message="Authentication required")

            if not ps.has_any(*perm_strings):
                from lexigram.admin.exceptions import PermissionDeniedError

                raise PermissionDeniedError(
                    message=f"Requires permission: {' or '.join(perm_strings)}",
                )

            return await func(*args, **kwargs)

        wrapper.__required_permissions__ = list(perm_strings)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def require_all_permissions(*permissions: str | Permission) -> Any:
    """Decorator to require ALL listed permissions on a handler.

    Checks ``request.state.permissions`` (a PermissionSet). Raises
    PermissionDeniedError if any permission is missing.

    Usage:
        @require_all_permissions("users.list", "users.view")
        async def view_users(request): ...
    """
    perm_strings = list(map(str, permissions))

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = args[0] if args else kwargs.get("request")
            if request is None:
                raise ValueError("No request object found for permission check")

            ps = _get_permission_set(request)
            if ps is None:
                from lexigram.admin.exceptions import PermissionDeniedError

                raise PermissionDeniedError(message="Authentication required")

            if not ps.has_all(*perm_strings):
                from lexigram.admin.exceptions import PermissionDeniedError

                raise PermissionDeniedError(
                    message=f"Requires all permissions: {', '.join(perm_strings)}",
                )

            return await func(*args, **kwargs)

        wrapper.__required_permissions__ = list(perm_strings)  # type: ignore[attr-defined]
        wrapper.__require_all__ = True  # type: ignore[attr-defined]
        return wrapper

    return decorator


def require_role(*roles: str) -> Any:
    """Decorator to require the user to have any of the listed roles.

    Checks ``request.user.roles`` (a list of role name strings). Raises
    PermissionDeniedError if the user has none of the required roles.

    Usage:
        @require_role("admin")
        async def admin_panel(request): ...

        @require_role("admin", "editor")
        async def editor_panel(request): ...
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = args[0] if args else kwargs.get("request")
            if request is None:
                raise ValueError("No request object found for role check")

            user = getattr(request, "user", None)
            if user is None:
                from lexigram.admin.exceptions import PermissionDeniedError

                raise PermissionDeniedError(message="Authentication required")

            user_roles = set(getattr(user, "roles", []) or [])
            if not user_roles.intersection(roles):
                from lexigram.admin.exceptions import PermissionDeniedError

                raise PermissionDeniedError(
                    message=f"Requires role: {' or '.join(roles)}",
                )

            return await func(*args, **kwargs)

        wrapper.__required_roles__ = list(roles)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def create_permission_context(
    user: Any,
    authorization_service: AuthorizationService,
) -> dict[str, Any]:
    """Create template context with permission helpers.

    Returns a dict containing the user object and callables that delegate
    to ``get_user_permissions`` so templates can check permissions without
    depending on a ``PermissionChecker`` class.

    Returns:
        Dict with ``user``, ``can``, ``can_any``, ``can_all``, ``has_role``,
        ``has_any_role``, and ``permissions`` keys.
    """
    perms = get_user_permissions(user, authorization_service)
    user_roles: set[str] = set(getattr(user, "roles", []) or [])
    return {
        "user": user,
        "can": perms.has,
        "can_any": perms.has_any,
        "can_all": perms.has_all,
        "has_role": lambda role: role in user_roles,
        "has_any_role": lambda *roles: bool(user_roles.intersection(roles)),
        "permissions": perms,
    }
