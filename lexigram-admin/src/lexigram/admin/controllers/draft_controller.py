from __future__ import annotations

from datetime import datetime
from typing import Any

from starlette.responses import HTMLResponse, JSONResponse

from lexigram.admin.controllers.base import AdminController
from lexigram.admin.services.forms.draft_service import (  # type: ignore[import-untyped]
    DraftService,
)
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class DraftController(AdminController):
    """Controller for handling form auto-save and draft retrieval."""

    def __init__(
        self, renderer: Any, draft_service: DraftService | None = None
    ) -> None:
        super().__init__(renderer)
        self.draft_service = draft_service or DraftService()

    @post("/api/forms/draft/{form_id}")
    async def save_draft(self, form_id: str, request) -> Any:
        """Save a form draft via HTMX pulse."""
        try:
            # Get user ID from request state
            state_user = getattr(getattr(request, "state", None), "user", None)
            user_id = (
                str(getattr(state_user, "user_id", "anonymous"))
                if state_user
                else "anonymous"
            )

            # Extract form data
            if request.headers.get("content-type") == "application/json":
                data = await request.json()
            else:
                form_data = await request.form()
                data = dict(form_data)

            # Prevent saving sensitive fields if necessary
            data.pop("csrf_token", None)
            data.pop("password", None)

            await self.draft_service.save_draft(form_id, user_id, data)

            # Return success indicator for UI
            timestamp = datetime.now().strftime("%H:%M:%S")
            return HTMLResponse(
                content=f'<span class="text-xs text-gray-400 italic">Draft saved at {timestamp}</span>',
                status_code=200,
            )

        except Exception as _save_err:  # noqa: BLE001 — controller boundary; autosave errors must not crash the request
            logger.exception("Failed to save draft for %s", form_id)
            return HTMLResponse(
                content='<span class="text-xs text-red-400">Autosave failed</span>',
                status_code=500,
            )

    @get("/api/forms/draft/{form_id}")
    async def get_draft(self, form_id: str, request) -> Any:
        """Retrieve a saved form draft."""
        try:
            state_user = getattr(getattr(request, "state", None), "user", None)
            user_id = (
                str(getattr(state_user, "user_id", "anonymous"))
                if state_user
                else "anonymous"
            )
            draft = await self.draft_service.get_draft(form_id, user_id)

            if not draft:
                return JSONResponse({"status": "not_found"}, status_code=404)

            return JSONResponse(
                {
                    "status": "success",
                    "data": draft.data,
                    "updated_at": draft.updated_at.isoformat(),
                },
            )

        except Exception as e:  # noqa: BLE001 — controller boundary; all errors become HTTP 500 responses
            logger.exception("Failed to retrieve draft for %s", form_id)
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
