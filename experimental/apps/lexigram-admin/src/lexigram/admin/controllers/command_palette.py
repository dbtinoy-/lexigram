"""Controller for the command palette endpoint."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.admin.resources.urls import admin_prefix_from_request, mount_admin_url
from lexigram.admin.services.search_service import SearchService
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_STATIC_COMMANDS: list[dict[str, Any]] = [
    {"label": "Go to Dashboard", "href": "/admin/", "icon": "home", "shortcut": "G D"},
    {
        "label": "Manage Users",
        "href": "/admin/users",
        "icon": "users",
        "shortcut": "G U",
    },
    {
        "label": "Toggle Dark Mode",
        "action": "darkMode = !darkMode",
        "icon": "moon",
        "shortcut": "T D",
    },
    {
        "label": "Settings",
        "href": "/admin/settings",
        "icon": "settings",
        "shortcut": ",",
    },
]

_MIN_QUERY_LENGTH = 2


@inject
class CommandPaletteController:
    """Handles the command palette search endpoint.

    Returns JSON commands that the frontend merges with static commands.
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search_service = search_service

    async def search(self, request: Request) -> JSONResponse:
        """Handle GET /admin/command-palette?q=..."""
        query = (request.query_params.get("q") or "").strip()
        commands: list[dict[str, Any]] = []

        admin_prefix = admin_prefix_from_request(request)

        # Filter static commands by query without mutating the shared defaults.
        for original in _STATIC_COMMANDS:
            cmd = dict(original)
            if cmd.get("href"):
                cmd["href"] = mount_admin_url(cmd["href"], admin_prefix)
            if not query or query.lower() in cmd["label"].lower():
                commands.append(cmd)

        # Dynamic search results from backend
        if len(query) >= _MIN_QUERY_LENGTH:
            try:
                user = getattr(request.state, "user", None)
                allowed = await self._search_service.allowed_resources_for(user)
                results = await self._search_service.search(
                    query, allowed_resources=allowed
                )
                for r in results.results:
                    commands.append(
                        {
                            "label": f"{r.resource_label}: {r.title}",
                            "href": mount_admin_url(r.url, admin_prefix),
                            "icon": "search",
                            "subtitle": r.subtitle,
                        }
                    )
            except Exception:
                logger.exception("Command palette search failed for query=%s", query)

        return JSONResponse(commands)
