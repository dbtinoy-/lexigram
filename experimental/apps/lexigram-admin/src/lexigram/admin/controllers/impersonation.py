"""Impersonation controller for the admin panel."""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route

from lexigram.admin.auth.store import AdminUserStoreProtocol
from lexigram.admin.services.impersonation import ImpersonationService
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class ImpersonationController:
    """Handles starting and stopping superadmin impersonation sessions.

    CSRF is validated by the global ``AdminCsrfMiddleware`` already applied
    to every admin POST route — this controller does not duplicate that
    check.
    """

    def __init__(
        self,
        service: ImpersonationService,
        user_store: AdminUserStoreProtocol,
    ) -> None:
        self._service = service
        self._user_store = user_store

    def get_routes(self) -> list[Any]:
        """Build routes explicitly, with the literal ``/impersonate/stop``
        path ordered before the parameterised ``/impersonate/{user_id}``
        path — Starlette matches routes in list order, and a
        dispatched-first ``{user_id}`` route would otherwise swallow
        ``/impersonate/stop`` (``user_id="stop"``).
        """
        return [
            Route(
                "/impersonate/stop",
                endpoint=self.stop_impersonation,
                methods=["POST"],
                name="admin_impersonation_stop",
            ),
            Route(
                "/impersonate/{user_id}",
                endpoint=self.start_impersonation,
                methods=["POST"],
                name="admin_impersonation_start",
            ),
        ]

    async def start_impersonation(self, request: Request) -> Response:
        """Start impersonating the target user (D4/D5)."""
        actor = getattr(request.state, "user", None)
        if actor is None:
            return self._toast_error("You must be signed in.", status_code=403)

        target_user_id = str(request.path_params.get("user_id", ""))

        target_roles: list[str] | None = None
        try:
            target = await self._user_store.get_user_by_id(target_user_id)
        except Exception:  # noqa: BLE001 — best-effort role lookup
            target = None
        if target is not None:
            target_roles = list(getattr(target, "roles", []) or [])

        result = await self._service.start(
            actor,
            target_user_id,
            request=request,
            target_roles=target_roles,
        )

        if result.is_err():
            error = result.unwrap_err()
            return self._toast_error(str(error), status_code=403)

        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/admin/users"
        return response

    async def stop_impersonation(self, request: Request) -> Response:
        """Stop the active impersonation session for the current actor (D4/D7)."""
        actor = getattr(request.state, "user", None)
        if actor is not None:
            result = await self._service.stop(actor, request)
            if result.is_err():
                from lexigram.admin.state.context import AdminContextManager

                async with AdminContextManager(request) as ctx:
                    ctx.add_flash("No active impersonation session to stop.", "warning")
        return RedirectResponse(url="/admin/", status_code=302)

    @staticmethod
    def _toast_error(message: str, *, status_code: int) -> Response:
        """Build an error response carrying an HX-Trigger toast event."""
        response = Response(content=message, status_code=status_code)
        response.headers["HX-Trigger"] = json.dumps(
            {"show-toast": {"message": message, "type": "error"}}
        )
        return response
