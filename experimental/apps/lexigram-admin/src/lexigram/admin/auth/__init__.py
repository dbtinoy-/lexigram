"""Admin authentication system.

Provides built-in authentication with YAML/env configuration, RBAC,
and secure session management.
"""

from __future__ import annotations

# RBACChecker removed - use AuthorizationService instead
# New integration module (lazy loaded for optional deps)
from typing import TYPE_CHECKING, Any

from lexigram.admin.auth.guard_chain import AdminGuardChain
from lexigram.admin.auth.models import GUEST_USER, AdminUser, Role
from lexigram.admin.auth.session_manager import AdminSessionManager
from lexigram.admin.auth.store import AbstractAdminUserStore
from lexigram.admin.config import AdminAuthConfig

_AUTH_LAZY_IMPORTS = {
    "require_auth": ".guards",
}

if TYPE_CHECKING:
    from lexigram.admin.auth.guards import (
        require_auth,
    )


def __getattr__(name: str) -> Any:
    if name in _AUTH_LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_AUTH_LAZY_IMPORTS[name], __package__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_AUTH_LAZY_IMPORTS.keys()))


__all__ = [
    "GUEST_USER",
    "AbstractAdminUserStore",
    "AdminAuthConfig",
    "AdminGuardChain",
    "AdminSessionManager",
    "AdminUser",
    "Role",
    "require_auth",
]
