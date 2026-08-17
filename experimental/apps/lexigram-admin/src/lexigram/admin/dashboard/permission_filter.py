from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from lexigram.admin.types import AdminUser

T = TypeVar("T")


class PermissionFilter:
    """Filters contributor surface items based on user permissions."""

    def filter(
        self,
        items: Sequence[T],
        user: AdminUser | None,
        get_required_permissions: Callable[[T], frozenset[str]],
    ) -> list[T]:
        """Return only items whose required permissions the *user* holds.

        If *user* is ``None`` only items with empty required_permissions
        are returned.
        """
        result: list[T] = []
        for item in items:
            perms = get_required_permissions(item)
            if not perms or (
                user is not None and perms.issubset(user.permissions or frozenset())
            ):
                result.append(item)
        return result
