from __future__ import annotations

from typing import Any, Protocol

from lexigram.ui import Component


class PermissionCheckProtocol(Protocol):
    """Protocol for permission check logic."""

    def can_handle(self, action: str) -> bool: ...
    async def check_permission(
        self,
        service: Any,
        user: Any,
        resource: str,
        action: str,
    ) -> bool: ...


class ViewPermissionChecker:
    def can_handle(self, action: str) -> bool:
        return action in ("read", "view", "list")

    async def check_permission(
        self,
        service: Any,
        user: Any,
        resource: str,
        action: str,
    ) -> bool:
        return await service.can_view(user, resource)


class CreatePermissionChecker:
    def can_handle(self, action: str) -> bool:
        return action == "create"

    async def check_permission(
        self,
        service: Any,
        user: Any,
        resource: str,
        action: str,
    ) -> bool:
        return await service.can_create(user, resource)


class EditPermissionChecker:
    def can_handle(self, action: str) -> bool:
        return action == "edit"

    async def check_permission(
        self,
        service: Any,
        user: Any,
        resource: str,
        action: str,
    ) -> bool:
        return await service.can_edit(user, resource)


class DeletePermissionChecker:
    def can_handle(self, action: str) -> bool:
        return action == "delete"

    async def check_permission(
        self,
        service: Any,
        user: Any,
        resource: str,
        action: str,
    ) -> bool:
        return await service.can_delete(user, resource)


class DefaultPermissionChecker:
    def can_handle(self, action: str) -> bool:
        return True

    async def check_permission(
        self,
        service: Any,
        user: Any,
        resource: str,
        action: str,
    ) -> bool:
        return await service.can_perform_action(user, resource, action)


class PermissionCheckRegistry:
    """Registry for permission checking logic."""

    def __init__(self) -> None:
        self._checkers: list[PermissionCheckProtocol] = [
            ViewPermissionChecker(),
            CreatePermissionChecker(),
            EditPermissionChecker(),
            DeletePermissionChecker(),
            DefaultPermissionChecker(),
        ]

    def get_checker(self, action: str) -> PermissionCheckProtocol:
        for checker in self._checkers:
            if checker.can_handle(action):
                return checker
        return DefaultPermissionChecker()


_permission_check_registry = PermissionCheckRegistry()


class PermissionGate(Component):
    """
    Renders children only if the user has the specified permission.

    Example:
        >>> PermissionGate(
        ...     resource="users",
        ...     action="delete",
        ...     user=request.user,
        ...     children=[DeleteButton()]
        ... )
    """

    def __init__(
        self,
        resource: str,
        action: str,
        user: Any,
        children: list[Component] | None = None,
        fallback: Component | None = None,
        permission_service: Any = None,
        allowed: bool | None = None,
        **props: Any,
    ):
        super().__init__(**props)
        self.resource = resource
        self.action = action
        self.user = user
        self.children = children or []
        self.fallback = fallback
        self._permission_service = permission_service
        self._allowed = allowed

    def render(self) -> Any:
        if self._allowed is not None:
            if self._allowed:
                return self.children
            return self.fallback or ""

        if self._permission_service is None:
            return self.children

        raise RuntimeError(
            "PermissionGate: permission checks are async; hoist the check to "
            "the async caller and pass resolved `allowed`"
        )
