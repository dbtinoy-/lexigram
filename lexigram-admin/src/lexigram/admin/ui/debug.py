"""Debug components for Lexigram Admin."""

from __future__ import annotations

from typing import Any

from lexigram.admin.services.session import SessionStateService
from lexigram.ui import Component, el


class StateDebugPanel(Component):
    """A panel to visualize and inspect the current session state.

    This component is intended for use during development to help
    debug stateful components and DI services.
    """

    def __init__(self, session: SessionStateService, **props: Any) -> None:
        super().__init__(**props)
        self.session = session

    def render(self) -> Any:
        # Resolve session items
        items = self.session.items()

        return el(
            "div",
            {
                "class": "state-debug-panel p-4 bg-gray-900 text-white rounded-lg shadow-xl font-mono text-xs border border-gray-700",
            },
            el(
                "h3",
                {"class": "text-sm font-bold mb-2 text-blue-400"},
                "🔍 Session State Debug",
            ),
            el(
                "div",
                {"class": "space-y-1 overflow-auto max-h-64"},
                [
                    el(
                        "div",
                        {"class": "flex justify-between border-b border-gray-800 py-1"},
                        el("span", {"class": "text-green-400"}, k),
                        el("span", {"class": "text-gray-300"}, str(v)),
                    )
                    for k, v in items
                ]
                if not self.session.is_empty
                else el(
                    "p",
                    {"class": "text-gray-500 italic"},
                    "No state data in current session.",
                ),
            ),
        )
