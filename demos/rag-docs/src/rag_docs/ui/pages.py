"""Console page — static serving only (logic lives in the API controller).

Lexigram pattern: page controllers serve HTML and static assets only.
All dynamic logic lives in API controllers — this file has zero
business logic, just file-serving routes.

Route handlers return ``FileResponse`` objects directly — the framework
serves them with the correct content type and cache headers.
"""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"
SHARED_ASSETS = UI_ROOT.parent.parent.parent.parent / "shared" / "assets"


def _view(name: str) -> FileResponse:
    """Serve one HTML view from ui/views/."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset from ui/static/."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class DocsPageController(Controller):
    """Serve the docs-ask console; every handler reads from ui/.

    Stateless — no constructor dependencies.  The framework instantiates
    this controller when a request matches its routes.
    """

    def __init__(self) -> None:
        """Stateless — no injected dependencies."""

    @get("/")
    async def console(self, request: Request) -> FileResponse:
        """The single-page split-screen console."""
        return _view("console.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        """Dark-theme split-screen stylesheet."""
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        """Vanilla-JS client (no build step)."""
        return _static("app.js", "text/javascript")

    @get("/static/logo.png")
    async def logo(self, request: Request) -> FileResponse:
        return FileResponse(path=SHARED_ASSETS / "logo.png", media_type="image/png")

    @get("/static/icon.png")
    async def icon(self, request: Request) -> FileResponse:
        return FileResponse(path=SHARED_ASSETS / "icon.png", media_type="image/png")


__all__ = ["DocsPageController"]
