"""Page controller — serves HTML views (optional).

For demos, we return simple dicts.  In production, you'd use
templates or an external frontend (React, Vue, etc.).
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class TasksPageController(Controller):
    """Page routes for the task management UI."""

    prefix = ""

    @get("/")
    async def index(self) -> dict[str, Any]:
        """Home page."""
        return {
            "title": "Task Manager",
            "description": "SQL Repository Demo — teaches lexigram-sql",
        }


__all__ = ["TasksPageController"]
