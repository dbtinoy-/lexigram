"""AdminAuthorizerProtocol — authorization for admin resource operations."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AdminAuthorizerProtocol(Protocol):
    """Canonical admin-internal authorization protocol.

    Covers both CRUD-level checks (can_view, can_create, can_update, can_delete)
    and action-level checks (can_execute_action).
    """

    async def can_view(self, user: Any, resource: str, record: Any = None) -> bool: ...

    async def can_create(self, user: Any, resource: str) -> bool: ...

    async def can_update(
        self, user: Any, resource: str, record: Any = None
    ) -> bool: ...

    async def can_delete(
        self, user: Any, resource: str, record: Any = None
    ) -> bool: ...

    async def can_execute_action(
        self, user: Any, resource: str, action: str, record: Any | None = None
    ) -> bool: ...


__all__ = ["AdminAuthorizerProtocol"]
