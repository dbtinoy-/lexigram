"""Page controller — serves HTML views (optional)."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class ContentPageController(Controller):
    """Page routes for the content generation UI."""

    prefix = ""

    @get("/")
    async def index(self) -> dict[str, Any]:
        """Home page."""
        return {
            "title": "Content Generator",
            "description": "LLM Router Demo — Demonstrates Lexigram LLM client pattern",
        }


__all__ = ["ContentPageController"]
