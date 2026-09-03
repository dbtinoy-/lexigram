"""Saved list views — save/delete endpoints (roadmap R13).

Per-user named list-view presets. The list page renders the views bar
(``ListRenderer._render_saved_views_bar``); applying a view is a plain
link, so this controller only needs the two POST mutations. Any signed-in
admin may manage their *own* views — no role gate, since the data is
strictly per-user. Design: docs/09-01-2026/08-saved-views.md.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.admin.auth.next_url import build_login_redirect
from lexigram.admin.controllers.access_control import _AccessControlController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.services.saved_views import SavedViewError, SavedViewService
from lexigram.contracts.web import post
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["SavedViewsController"]


class SavedViewsController(_AccessControlController):
    """Save/delete per-user list views.

    Routes:
        POST /admin/views/{resource_name}/save   - Save the current view
        POST /admin/views/{resource_name}/delete - Delete a saved view
    """

    prefix = "/views"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        saved_view_service: SavedViewService | None = None,
        super_admin_role: str = "superadmin",
    ) -> None:
        """Initialise the saved-views controller.

        Args:
            renderer: AdminRenderer (unused for pages; base requirement).
            csrf_service: CSRF token service (POST protection).
            saved_view_service: Storage service (wired at mount time).
            super_admin_role: Kept for base-class compatibility only.
        """
        super().__init__(
            renderer=renderer,
            csrf_service=csrf_service,
            super_admin_role=super_admin_role,
        )
        self._saved_view_service = saved_view_service

    # -- guard ---------------------------------------------------------------

    def _guard(self, request: Request) -> Response | None:
        """Require a signed-in admin only — saved views are per-user data."""
        user = self.current_user(request)
        if not user or getattr(user, "user_id", "guest") == "guest":
            return RedirectResponse(
                url=build_login_redirect(
                    self._admin_path(request, "/admin/login"),
                    str(request.url.path),
                ),
                status_code=302,
            )
        return None

    # -- helpers -------------------------------------------------------------

    def _csrf_ok(self, request: Request, csrf_token: str) -> bool:
        """Validate the token with the same session-id chain as the middleware.

        List pages mint their CSRF token from ``csrf_session_id`` *or*
        ``admin_user_id`` (see ``CsrfMiddleware`` and
        ``ListRenderer._ensure_csrf_token``); the base implementation only
        accepts ``csrf_session_id``, which regular list sessions don't have.
        """
        if self._csrf_service is None:
            return True
        session = getattr(request, "session", None) or {}
        session_id = str(
            session.get("csrf_session_id") or session.get("admin_user_id") or ""
        )
        return bool(
            session_id and self._csrf_service.validate_token(session_id, csrf_token)
        )

    def _list_url(self, request: Request, resource: str, query: str = "") -> str:
        """Canonical list URL for a resource, optionally with a query string."""
        base = self._admin_path(request, "/admin").rstrip("/")
        url = f"{base}/{resource}"
        return f"{url}?{query}" if query else url

    def _service(self, request: Request) -> SavedViewService | None:
        """Mount-wired service, falling back to app state (renderer path)."""
        if self._saved_view_service is not None:
            return self._saved_view_service
        state = getattr(getattr(request, "app", None), "state", None)
        service = getattr(state, "saved_view_service", None)
        return service if isinstance(service, SavedViewService) else None

    # -- routes --------------------------------------------------------------

    @post("/{resource_name:str}/save")
    async def save(self, request: Request, resource_name: str) -> Response:
        """Persist the submitted query string as a named view."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        list_url = self._list_url(request, resource_name)
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(
                list_url, "Invalid or expired form token.", is_error=True
            )
        service = self._service(request)
        if service is None:
            return self._redirect(
                list_url, "Saved views are unavailable.", is_error=True
            )
        user_id = self._actor_id(request) or ""
        name = str(form.get("name", ""))
        query = str(form.get("query", ""))
        try:
            entry = await service.save_view(user_id, resource_name, name, query)
        except SavedViewError as exc:
            return self._redirect(list_url, str(exc), is_error=True)
        return self._redirect(
            self._list_url(request, resource_name, entry["query"]),
            f"View \u201c{entry['name']}\u201d saved.",
        )

    @post("/{resource_name:str}/delete")
    async def delete(self, request: Request, resource_name: str) -> Response:
        """Delete one of the acting admin's saved views by name."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        list_url = self._list_url(request, resource_name)
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(
                list_url, "Invalid or expired form token.", is_error=True
            )
        service = self._service(request)
        if service is None:
            return self._redirect(
                list_url, "Saved views are unavailable.", is_error=True
            )
        user_id = self._actor_id(request) or ""
        name = str(form.get("name", ""))
        try:
            removed = await service.delete_view(user_id, resource_name, name)
        except SavedViewError as exc:
            return self._redirect(list_url, str(exc), is_error=True)
        if not removed:
            return self._redirect(list_url, "View not found.", is_error=True)
        return self._redirect(list_url, "View deleted.")
