"""GraphQL permission classes for field-level authorization.

This module provides permission classes that can be used to control
access to GraphQL fields, mutations, and subscriptions at the field level.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from lexigram.di.decorators import singleton

if TYPE_CHECKING:
    from strawberry import Info

    from lexigram.graphql.core.context import GraphQLContext


class AbstractPermission(abc.ABC):
    """Base class for GraphQL permissions.

    Permission classes control access to GraphQL fields. They are checked
    before field resolution and can raise exceptions or return False to
    deny access.

    Attributes:
        message: Error message when permission is denied.

    Example:
        ```python
        class IsAuthenticated(AbstractPermission):
            message = "Authentication required"

            async def has_permission(self, source, info, **kwargs):
                return info.context.user is not None

        @strawberry.type
        class User:
            @field(permission_classes=[IsAuthenticated])
            async def email(self) -> str:
                return self._email
        ```
    """

    message: str = "Permission denied"

    @abc.abstractmethod
    async def has_permission(
        self,
        source: Any,
        info: Info,
        **kwargs: Any,
    ) -> bool:
        """Check if the permission is granted.

        Args:
            source: The source object (parent resolver result).
            info: GraphQL resolver info containing context.
            **kwargs: Additional arguments passed to the field.

        Returns:
            True if permission is granted, False otherwise.

        Raises:
            Exception: If permission is denied with a custom error.
        """
        ...


@singleton
class IsAuthenticated(AbstractPermission):
    """Permission that requires user authentication."""

    message = "Authentication required"

    async def has_permission(
        self,
        source: Any,
        info: Info[Any, Any],
        **kwargs: Any,
    ) -> bool:
        """Check if user is authenticated."""
        context: GraphQLContext = info.context
        return context.user is not None


@singleton
class IsAdmin(AbstractPermission):
    """Permission that requires admin role."""

    message = "Admin access required"

    async def has_permission(
        self,
        source: Any,
        info: Info[Any, Any],
        **kwargs: Any,
    ) -> bool:
        """Check if user has admin role."""
        context: GraphQLContext = info.context
        if not context.user:
            return False

        # Check for admin role - adjust based on your user model
        user_roles = getattr(context.user, "roles", [])
        return "admin" in user_roles or "superuser" in user_roles


@singleton
class IsOwner(AbstractPermission):
    """Permission that requires ownership of the resource."""

    message = "Access denied: not the owner"

    async def has_permission(
        self,
        source: Any,
        info: Info[Any, Any],
        **kwargs: Any,
    ) -> bool:
        """Check if user owns the resource."""
        context: GraphQLContext = info.context
        if not context.user:
            return False

        # Check if source has user_id or owner_id field
        source_user_id = None
        user_id_attr = getattr(source, "user_id", None)
        if isinstance(user_id_attr, (str, int)):
            source_user_id = user_id_attr
        else:
            owner_id_attr = getattr(source, "owner_id", None)
            if isinstance(owner_id_attr, (str, int)):
                source_user_id = owner_id_attr

        if source_user_id is None:
            return False

        # Compare with current user ID
        current_user_id = None
        user_id_attr = getattr(context.user, "user_id", None)
        if isinstance(user_id_attr, (str, int)):
            current_user_id = user_id_attr
        else:
            id_attr = getattr(context.user, "id", None)
            if isinstance(id_attr, (str, int)):
                current_user_id = id_attr

        if current_user_id is None:
            return False

        return source_user_id == current_user_id


@singleton
class IsOwnerOrAdmin(AbstractPermission):
    """Permission that requires ownership or admin role."""

    message = "Access denied: not the owner or admin"

    async def has_permission(
        self,
        source: Any,
        info: Info[Any, Any],
        **kwargs: Any,
    ) -> bool:
        """Check if user owns the resource or is admin."""
        # First check ownership
        owner_perm = IsOwner()
        if await owner_perm.has_permission(source, info, **kwargs):
            return True

        # Then check admin
        admin_perm = IsAdmin()
        return await admin_perm.has_permission(source, info, **kwargs)


@singleton
class AllowAny(AbstractPermission):
    """Permission that allows any access (no restrictions)."""

    message = "This should never be shown"

    async def has_permission(
        self,
        source: Any,
        info: Info[Any, Any],
        **kwargs: Any,
    ) -> bool:
        """Always allow access."""
        return True


@singleton
class DenyAll(AbstractPermission):
    """Permission that denies all access."""

    message = "Access denied"

    async def has_permission(
        self,
        source: Any,
        info: Info[Any, Any],
        **kwargs: Any,
    ) -> bool:
        """Always deny access."""
        return False


# Convenience instances for common permissions
# Note: These use fallback instances. For DI-integrated permissions,
# resolve them at request time using the container.
is_authenticated = IsAuthenticated()
is_admin = IsAdmin()
is_owner = IsOwner()
is_owner_or_admin = IsOwnerOrAdmin()
allow_any = AllowAny()
deny_all = DenyAll()


__all__ = [
    "AbstractPermission",
    "AllowAny",
    "DenyAll",
    "IsAdmin",
    "IsAuthenticated",
    "IsOwner",
    "IsOwnerOrAdmin",
    "allow_any",
    "deny_all",
    "is_admin",
    "is_authenticated",
    "is_owner",
    "is_owner_or_admin",
]
