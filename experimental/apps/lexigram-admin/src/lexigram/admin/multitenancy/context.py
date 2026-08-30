"""Request-local tenant context used by tenant-aware data sources."""

from __future__ import annotations

from contextvars import ContextVar, Token

_current_tenant: ContextVar[str | None] = ContextVar(
    "lexigram_admin_current_tenant",
    default=None,
)


def set_current_tenant(tenant_id: str | None) -> Token[str | None]:
    """Set the tenant for the current request/task and return its reset token."""
    return _current_tenant.set(tenant_id)


def reset_current_tenant(token: Token[str | None]) -> None:
    """Restore the tenant context represented by *token*."""
    _current_tenant.reset(token)


def get_current_tenant() -> str | None:
    """Return the tenant bound to the current request/task, if any."""
    return _current_tenant.get()


__all__ = ["get_current_tenant", "reset_current_tenant", "set_current_tenant"]
