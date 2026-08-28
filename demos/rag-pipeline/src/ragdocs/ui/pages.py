"""RAG pipeline page controller — static serving only.

Convention followed: **Page controller pattern** — ``RagPageController``
serves the static HTML/CSS/JS files for the single-page console.  All
dynamic behavior is handled by the API controller.

Routes:

- ``GET /``            — the RAG console (``rag.html``)
- ``GET /static/style.css`` — stylesheet
- ``GET /static/app.js``    — vanilla JS client
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
    """Serve one HTML view."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class RagPageController(Controller):
    """Serve the RAG console; every handler reads from ui/."""

    def __init__(self) -> None:
        """Stateless."""

    @get("/")
    async def console(self, request: Request) -> FileResponse:
        """The single-page console."""
        return _view("rag.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")

    @get("/static/logo.png")
    async def logo(self, request: Request) -> FileResponse:
        return FileResponse(path=SHARED_ASSETS / "logo.png", media_type="image/png")

    @get("/static/icon.png")
    async def icon(self, request: Request) -> FileResponse:
        return FileResponse(path=SHARED_ASSETS / "icon.png", media_type="image/png")


__all__ = ["RagPageController"]
