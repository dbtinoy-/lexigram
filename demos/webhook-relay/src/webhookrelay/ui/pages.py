"""Page controller — serves HTML views (optional)."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class WebhookPageController(Controller):
    """Page routes for the webhook relay UI."""

    prefix = ""

    @get("/")
    async def index(self) -> dict[str, Any]:
        """Home page."""
        return {
            "title": "Webhook Relay",
            "description": "Webhook Relay Demo — Demonstrates Lexigram webhook pattern",
        }


__all__ = ["WebhookPageController"]
