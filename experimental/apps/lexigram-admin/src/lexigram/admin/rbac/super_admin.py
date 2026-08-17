"""Super-admin detection for the RBAC admin subsystem.

The super-admin role name is configurable via
``AdminRbacConfig.super_admin_role`` (default ``"superadmin"`` — the
string existing controllers and impersonation already special-case).
"""

from __future__ import annotations

from typing import Any


def is_super_admin(user: Any, super_admin_role: str) -> bool:
    """Return True when the user holds the configured super-admin role.

    Args:
        user: User-like object exposing ``roles`` (list or tuple of str).
        super_admin_role: Role name that grants super-admin rights.

    Returns:
        ``True`` when the role is present in the user's roles.
    """
    roles = getattr(user, "roles", None) or ()
    return super_admin_role in roles


__all__ = ["is_super_admin"]
