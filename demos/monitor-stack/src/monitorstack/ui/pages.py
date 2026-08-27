"""Page controller — serves HTML views (optional)."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class MonitorPageController(Controller):
    """Page routes for the monitor stack UI."""

    prefix = ""

    @get("/")
    async def index(self) -> dict[str, Any]:
        """Home page."""
        return {
            "title": "Monitor Stack",
            "description": "Monitor Stack Demo — teaches Lexigram monitoring pattern",
        }


__all__ = ["MonitorPageController"]
