"""Content negotiation for admin error responses.

Shared by :class:`AdminErrorMiddleware` and
:class:`AdminAuthorizationMiddleware` so that every 403/404/405/500 the
admin produces obeys the same rule (roadmap R7):

- **Browser navigations** (``Accept: text/html``, not HTMX, not JSON) get
  the styled standalone error page.
- **HTMX fragment requests** keep fragment/HX-header semantics (handled by
  the callers).
- **API callers** (``Accept: application/json`` or the admin API prefix)
  keep machine-readable JSON.

Everything here is intentionally dependency-light so both middlewares can
import it without cycles.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import HTMLResponse

#: Status codes eligible for a styled HTML page when the client is a browser.
NEGOTIABLE_STATUS_CODES = frozenset({403, 404, 405, 500})

#: status -> (title, user-facing message, icon)
ERROR_PAGE_META: dict[int, tuple[str, str, str]] = {
    403: (
        "Access Denied",
        "You don't have permission to access this resource.",
        "🔒",
    ),
    404: (
        "Page Not Found",
        "The page you're looking for could not be found.",
        "🔍",
    ),
    405: (
        "Method Not Allowed",
        "That action isn't available for this page.",
        "⚠️",
    ),
    500: (
        "Internal Server Error",
        "Something went wrong on our end.",
        "💥",
    ),
}

_DEFAULT_META = ("Error", "An unexpected error occurred.", "⚠️")


def prefers_html(request: Request) -> bool:
    """Return True when the client is a browser navigation expecting HTML.

    A client that explicitly accepts JSON keeps JSON even if it also accepts
    HTML with a lower priority — API clients commonly send both, browsers
    send ``text/html`` first without ``application/json``.
    """
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def error_page_meta(status_code: int) -> tuple[str, str, str]:
    """Return ``(title, message, icon)`` for *status_code*."""
    return ERROR_PAGE_META.get(status_code, _DEFAULT_META)


def styled_error_response(
    status_code: int,
    admin_prefix: str = "/admin",
) -> HTMLResponse:
    """Build the styled standalone error page response for *status_code*."""
    from lexigram.admin.lib.template import render_error_page

    prefix = (admin_prefix or "/admin").rstrip("/")
    title, message, icon = error_page_meta(status_code)
    html = render_error_page(
        status_code=status_code,
        title=title,
        message=message,
        icon=icon,
        action_text="Go to Dashboard",
        action_url=f"{prefix}/",
        base_url=prefix,
    )
    return HTMLResponse(html, status_code=status_code)


__all__ = [
    "ERROR_PAGE_META",
    "NEGOTIABLE_STATUS_CODES",
    "error_page_meta",
    "prefers_html",
    "styled_error_response",
]
