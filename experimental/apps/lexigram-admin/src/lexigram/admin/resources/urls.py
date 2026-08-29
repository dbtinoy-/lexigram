"""Admin URL helpers for the resource pipeline.

The admin panel is mounted at a configurable prefix (``AdminConfig.prefix``,
default ``/admin``). Every redirect/URL built by the resource pipeline must
use the configured prefix — hard-coded ``/admin`` paths break custom-prefix
deployments. These helpers resolve the prefix from the request and build
resource URLs from it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

DEFAULT_ADMIN_PREFIX = "/admin"


def admin_prefix_from_request(request: Any) -> str:
    """Resolve the configured admin prefix for a request.

    Resolution order:

    1. ``scope["admin_prefix"]`` — set by ``ResourceHandler.__call__``.
    2. ``request.app.state.admin_prefix`` — set by the bundle mount phase
       (``_mount_app_state``) for controller pages.
    3. The framework default (``/admin``) — keeps standalone/unit usage and
       legacy scopes working.

    Args:
        request: A Starlette request (or object exposing ``scope``).

    Returns:
        The admin prefix without a trailing slash.
    """
    scope = getattr(request, "scope", None)
    if isinstance(scope, Mapping):
        prefix = scope.get("admin_prefix")
        if isinstance(prefix, str) and prefix:
            return prefix.rstrip("/")

    app = getattr(request, "app", None)
    app_state = getattr(app, "state", None)
    if app_state is not None:
        state_prefix = getattr(app_state, "admin_prefix", None)
        if isinstance(state_prefix, str) and state_prefix:
            return state_prefix.rstrip("/")

    return DEFAULT_ADMIN_PREFIX


def admin_url(
    prefix: str,
    resource_name: str,
    suffix: str = "",
    query: str | None = None,
) -> str:
    """Build an admin resource URL from its parts.

    Args:
        prefix: Admin mount prefix (e.g. ``/admin`` or ``/backoffice``).
        resource_name: Resource name (e.g. ``users``); may be empty for
            top-level admin pages.
        suffix: Optional route suffix (e.g. ``"1/edit"``).
        query: Optional query string without a leading ``?``
            (e.g. ``"notice=Saved."``).

    Returns:
        A normalized absolute path, e.g. ``/admin/users/1/edit``.
    """
    base = (prefix or DEFAULT_ADMIN_PREFIX).rstrip("/")
    name = (resource_name or "").strip("/")
    path = f"{base}/{name}" if name else base
    if suffix:
        path = f"{path}/{suffix.lstrip('/')}"
    if query:
        path = f"{path}?{query.lstrip('?')}"
    return path


__all__ = ["DEFAULT_ADMIN_PREFIX", "admin_prefix_from_request", "admin_url"]
