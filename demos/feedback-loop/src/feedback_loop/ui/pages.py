"""Console page — static serving only (logic lives in the API controller).

Convention: page controllers serve HTML views and static assets.  The
single-page console (``loop.html``) makes API calls to ``/api/*``
endpoints; all business logic lives in ``controllers/api.py``.
"""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"


def _view(name: str) -> FileResponse:
    """Serve one HTML view."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class LoopPageController(Controller):
    """Serve the feedback-loop console; every handler reads from ui/."""

    def __init__(self) -> None:
        """Stateless."""

    @get("/")
    async def console(self, request: Request) -> FileResponse:
        """The single-page console."""
        return _view("loop.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")



__all__ = ["LoopPageController"]
