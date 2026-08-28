"""Static UI file-serving routes (no logic — assets only)."""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"
SHARED_ASSETS = UI_ROOT.parent.parent.parent.parent / "shared" / "assets"


def _view(name: str) -> FileResponse:
    """Serve one HTML view."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class PagesController(Controller):
    """Serve the dashboard HTML/CSS/JS; all logic lives in the API controller."""

    @get("/")
    async def index(self, request: Request) -> FileResponse:
        """The dashboard page — the vanilla-JS client owns all behaviour.

        The SSE stream (``/api/events/stream``) replays recent history on
        connect, so the page itself is fully static.
        """
        return _view("index.html")

    @get("/static/dashboard.js")
    async def dashboard_js(self, request: Request) -> FileResponse:
        return _static("dashboard.js", "text/javascript")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/logo.png")
    async def logo(self, request: Request) -> FileResponse:
        return FileResponse(path=SHARED_ASSETS / "logo.png", media_type="image/png")

    @get("/static/icon.png")
    async def icon(self, request: Request) -> FileResponse:
        return FileResponse(path=SHARED_ASSETS / "icon.png", media_type="image/png")


__all__ = ["PagesController"]
