"""Error Boundary component for Lexigram Admin."""

from __future__ import annotations

from typing import Any

from lexigram.logging import get_logger
from lexigram.ui.core.base import Component, el, render_to_string
from lexigram.ui.molecules.error_state import ErrorState

logger = get_logger(__name__)


class ErrorBoundary(Component):
    """Component that catches rendering errors in its children.

    This provides a fallback UI when a sub-component fails to render,
    preventing the entire page from breaking.
    """

    def __init__(self, fallback: Any | None = None, **props) -> None:
        super().__init__(**props)
        self.fallback = fallback

    def render(self) -> Any:
        try:
            # Force rendering of children to catch exceptions early
            content = render_to_string(self.children)
            return el("div", content, **self.props)
        except Exception as e:  # error boundary must catch all rendering errors
            logger.exception("Error rendering component inside ErrorBoundary")
            if self.fallback:
                return el("div", self.fallback, role="alert")

            return el(
                "div",
                ErrorState(
                    title="Rendering Error",
                    message=f"A component failed to display: {e!s}",
                    action=el(
                        "button",
                        "Reload Page",
                        onclick="window.location.reload()",
                        class_="px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors",
                    ),
                ),
                role="alert",
            )
