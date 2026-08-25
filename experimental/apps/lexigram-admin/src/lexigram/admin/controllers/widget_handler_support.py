"""Shared plumbing for widget controller handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.admin.auth.types import AdminSecurityEventType


def csrf_token_for(csrf_service: Any, request: Request) -> str | None:
    """Resolve the CSRF token for form rendering, if available."""
    if not csrf_service:
        return None
    try:
        session = getattr(request, "session", {})
        session_id: str = session.get("admin_user_id", "")
        return csrf_service.generate_token(session_id)
    except Exception:  # noqa: BLE001 — non-fatal for form rendering
        return None


async def ensure_edit_allowed(
    user_has_edit_permission: Callable[[Request], bool],
    audit: Callable[..., Awaitable[None]],
    request: Request,
    route: str,
) -> HTMLResponse | None:
    """Deny widget-pref mutations when the user may not edit.

    Returns:
        A 403 response after auditing the denial, or ``None`` when allowed.
    """
    if not user_has_edit_permission(request):
        await audit(
            request,
            success=False,
            event_type=AdminSecurityEventType.PERMISSION_DENIED,
            reason="permission_denied",
            route=route,
        )
        return HTMLResponse("Permission denied", status_code=403)
    return None
