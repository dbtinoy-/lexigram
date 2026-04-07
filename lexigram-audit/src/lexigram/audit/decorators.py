"""Consumer-facing decorators for audit logging."""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def audited(
    action: str,
    *,
    resource_type: str = "",
    severity: str = "medium",
) -> Callable[[F], F]:
    """Mark an async function for automatic audit logging.

    Attaches audit metadata that an audit middleware or interceptor can
    read to automatically log an ``AuditEntry`` on successful execution.

    Args:
        action: Dot-notation action identifier (e.g. ``"user.update"``).
        resource_type: Kind of affected resource (e.g. ``"User"``).
        severity: Default severity level for the audit entry.

    Returns:
        Decorator that attaches audit metadata to the function.

    Example::

        @audited("user.update", resource_type="User", severity="medium")
        async def update_user(self, user_id: str, data: dict) -> User:
            ...
    """

    def decorator(fn: F) -> F:
        fn.__audited__ = True  # type: ignore[attr-defined]
        fn.__audit_action__ = action  # type: ignore[attr-defined]
        fn.__audit_resource_type__ = resource_type  # type: ignore[attr-defined]
        fn.__audit_severity__ = severity  # type: ignore[attr-defined]

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["audited"]
