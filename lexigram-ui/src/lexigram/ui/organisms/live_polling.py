"""Live polling / auto-refresh component.

Provides an HTMX-powered ``AutoRefreshWidget`` that automatically
re-fetches content at a configurable interval — the "Live polling /
auto-refresh" feature from the benchmark matrix (FilamentPHP Y, React Admin Y).

Usage in a controller::

    widget = AutoRefreshWidget(
        url="/admin/dashboard/stats",
        interval_ms=5000,
        target_id="stats-panel",
        label="Auto-refresh",
    )
    # Render the container div once; HTMX polls automatically.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class AutoRefreshWidget(Component):
    """HTMX polling container that re-fetches *url* every *interval_ms* ms.

    The component renders a ``<div>`` with ``hx-get`` and
    ``hx-trigger="every <N>ms"`` attributes.  The polled response should
    return an HTML fragment that replaces ``innerHTML`` of the container.

    A "Pause / Resume" toggle button (Alpine.js) lets users stop polling
    without a page reload.

    Args:
        url: Endpoint to poll (HTMX GET).
        interval_ms: Polling interval in milliseconds (default 5000).
        target_id: ``id`` given to the wrapper element, used as the HTMX
            target selector for OOB swaps.
        content: Optional initial HTML content rendered before first poll.
        label: Optional label shown next to the pause/resume button.
        show_controls: Whether to render the pause/resume button.
    """

    def __init__(
        self,
        url: str,
        interval_ms: int = 5000,
        target_id: str = "auto-refresh-widget",
        content: Any = "",
        label: str = "",
        show_controls: bool = True,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.url = url
        self.interval_ms = interval_ms
        self.target_id = target_id
        self.content = content
        self.label = label
        self.show_controls = show_controls

    def render(self) -> Any:
        controls = self._render_controls() if self.show_controls else ""

        return el(
            "div",
            controls,
            el(
                "div",
                self.content,
                id=self.target_id + "-content",
                **{
                    "hx-get": self.url,
                    "hx-trigger": f"every {self.interval_ms}ms [!paused]",
                    "hx-target": "this",
                    "hx-swap": "innerHTML",
                    "hx-indicator": f"#{self.target_id}-spinner",
                    "x-bind:data-paused": "paused",
                },
            ),
            self._render_spinner(),
            id=self.target_id,
            class_="relative",
            **{
                "x-data": "{ paused: false }",
            },
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_controls(self) -> Any:
        label_el = (
            el(
                "span",
                self.label,
                class_="text-xs text-muted-foreground mr-2",
            )
            if self.label
            else ""
        )

        return el(
            "div",
            label_el,
            # Pause button
            el(
                "button",
                el(
                    "span",
                    "Pause",
                    **{"x-show": "!paused"},
                    style="display:inline",
                ),
                el(
                    "span",
                    "Resume",
                    **{"x-show": "paused", "x-cloak": ""},
                ),
                type="button",
                class_=(
                    "inline-flex items-center gap-1 px-2 py-1 text-xs "
                    "rounded border border-border "
                    "bg-card "
                    "text-muted-foreground dark:text-foreground "
                    "hover:bg-muted dark:hover:bg-muted "
                    "transition-colors"
                ),
                **{"@click": "paused = !paused"},
            ),
            class_="flex items-center justify-end mb-2",
        )

    def _render_spinner(self) -> Any:
        return el(
            "div",
            el(
                "svg",
                el(
                    "circle",
                    cx="12",
                    cy="12",
                    r="10",
                    stroke="currentColor",
                    **{"stroke-width": "4", "fill": "none", "class": "opacity-25"},
                ),
                el(
                    "path",
                    fill="currentColor",
                    d="M4 12a8 8 0 018-8v8z",
                    **{"class": "opacity-75"},
                ),
                xmlns="http://www.w3.org/2000/svg",
                fill="none",
                viewBox="0 0 24 24",
                class_="animate-spin w-4 h-4 text-primary",
            ),
            id=self.target_id + "-spinner",
            class_="htmx-indicator absolute top-2 right-2",
        )


class LiveDataTable(AutoRefreshWidget):
    """Auto-refreshing data table variant.

    Convenience subclass with table-appropriate defaults:
    longer interval and no pause/resume controls by default.

    Args:
        url: Endpoint returning updated table HTML fragment.
        interval_ms: Polling interval (default 30 000 ms = 30 s).
        target_id: Wrapper element ID.
        show_controls: Whether to show pause button (default True).
    """

    def __init__(
        self,
        url: str,
        interval_ms: int = 30_000,
        target_id: str = "live-data-table",
        show_controls: bool = True,
        **props: Any,
    ) -> None:
        super().__init__(
            url=url,
            interval_ms=interval_ms,
            target_id=target_id,
            show_controls=show_controls,
            **props,
        )
