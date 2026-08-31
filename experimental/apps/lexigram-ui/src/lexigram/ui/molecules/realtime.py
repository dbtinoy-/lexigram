"""Real-time UI components for Lexigram Admin."""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el
from lexigram.ui.htmx.attrs import hx_get, hx_swap, hx_target, hx_trigger


class RealTimeFeed(Component):
    """A component that polls or uses SSE to update its content in real-time.

    Example:
        ```python
        feed = RealTimeFeed(
            url="/admin/updates",
            interval="5s",
            content=el("p", "Waiting for updates...")
        )
        ```
    """

    def __init__(
        self,
        url: str,
        interval: str | None = "10s",
        use_sse: bool = False,
        content: Any = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.url = url
        self.interval = interval
        self.use_sse = use_sse
        self.initial_content = content or el(
            "div",
            {"class": "animate-pulse h-4 bg-muted rounded w-3/4"},
        )

    def render(self) -> Any:
        attrs = {
            "class": "real-time-feed",
            "id": self.props.get("id", "feed-" + str(id(self))),
        }

        if self.use_sse:
            attrs.update(
                {"hx-ext": "sse", "sse-connect": self.url, "sse-swap": "message"},
            )
        elif self.interval:
            attrs.update(hx_get(self.url))
            attrs.update(hx_trigger(f"every {self.interval}"))
            attrs.update(hx_target("this"))
            attrs.update(hx_swap("innerHTML"))

        return el("div", attrs, self.initial_content)


class LiveCounter(Component):
    """A simple counter that updates in real-time."""

    def __init__(self, label: str, url: str, interval: str = "5s", **props: Any):
        super().__init__(**props)
        self.label = label
        self.url = url
        self.interval = interval

    def render(self) -> Any:
        return el(
            "div",
            {
                "class": "p-4 bg-card rounded-lg shadow sm:p-6 transition-colors duration-300",
            },
            el(
                "dt",
                {"class": "text-sm font-medium text-muted-foreground truncate"},
                self.label,
            ),
            el(
                "dd",
                {"class": "mt-1 text-3xl font-semibold text-foreground"},
                RealTimeFeed(url=self.url, interval=self.interval, content="--"),
            ),
        )
