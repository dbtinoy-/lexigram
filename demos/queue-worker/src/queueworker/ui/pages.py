"""Page controller — serves HTML views (optional)."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class QueuePageController(Controller):
    """Page routes for the queue worker UI."""

    prefix = ""

    @get("/")
    async def index(self) -> dict[str, Any]:
        """Home page."""
        return {
            "title": "Queue Worker",
            "description": "Queue Worker Demo — Demonstrates Lexigram queue pattern",
        }


__all__ = ["QueuePageController"]
