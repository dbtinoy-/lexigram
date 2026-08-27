"""Page controller — serves HTML views (optional)."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class RagPageController(Controller):
    """Page routes for the RAG pipeline UI."""

    prefix = ""

    @get("/")
    async def index(self) -> dict[str, Any]:
        """Home page."""
        return {
            "title": "RAG Pipeline",
            "description": "RAG Pipeline Demo — Demonstrates Lexigram RAG pipeline pattern",
        }


__all__ = ["RagPageController"]
