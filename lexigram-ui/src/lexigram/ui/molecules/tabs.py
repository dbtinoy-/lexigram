from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Tabs(Component):
    """
    A responsive tabbed interface component with smooth animations and client-side switching.

    Args:
        tabs: List of (label, id) or (label, url) tuples
        active_tab: Initially active tab ID or label
        client_side: If True, uses Alpine.js for content switching without page load
    """

    def __init__(
        self,
        tabs: list[tuple[str, str]],
        active_tab: str | None = None,
        client_side: bool = True,
        **props,
    ):
        super().__init__(**props)
        self.tabs = tabs
        self.active_id = active_tab or (tabs[0][1] if tabs else "")
        self.client_side = client_side

    def render(self) -> Any:
        # Alpine state for client side or simple selection for URL based
        x_data = f"{{ activeTab: '{self.active_id}' }}" if self.client_side else None

        attrs: dict[str, Any] = {}
        if x_data:
            attrs["x_data"] = x_data

        tab_values = [v for _, v in self.tabs]
        keyboard_nav: dict[str, str] = {}
        if self.client_side and tab_values:
            keyboard_nav = {
                "x-on:keydown.left.prevent": f"const i = {tab_values}.indexOf(activeTab); if (i > 0) activeTab = {tab_values}[i - 1]",
                "x-on:keydown.right.prevent": f"const i = {tab_values}.indexOf(activeTab); if (i < {len(tab_values)} - 1) activeTab = {tab_values}[i + 1]",
            }

        return el(
            "div",
            # Mobile dropdown
            el(
                "div",
                el("label", "Select a tab", for_="tabs", class_="sr-only"),
                el(
                    "select",
                    *[
                        el(
                            "option",
                            label,
                            value=value,
                            selected=(value == self.active_id),
                        )
                        for label, value in self.tabs
                    ],
                    id="tabs",
                    name="tabs",
                    class_="block w-full h-10 rounded-md border-border focus:border-ring focus-visible:ring-ring bg-background text-foreground",
                    **(
                        {"x_model": "activeTab"}
                        if self.client_side
                        else {
                            "x_on_change": "window.location.href = $event.target.value",
                        }
                    ),
                ),
                class_="sm:hidden mb-4",
            ),
            # Desktop tabs
            el(
                "div",
                el(
                    "nav",
                        *[
                            el(
                                "a" if not self.client_side else "button",
                                label,
                                class_="inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 "
                                + (
                                    "bg-background text-foreground shadow"
                                    if value == self.active_id
                                    else "text-muted-foreground hover:text-foreground"
                                ),
                                aria_current=(
                                    "page" if value == self.active_id else None
                                ),
                                **(
                                    {
                                        "href": value,
                                        "hx_get": value
                                        if value.startswith("/")
                                        else None,
                                        "hx_target": "#main-content",
                                        "hx_swap": "innerHTML",
                                        "hx_push_url": "true",
                                    }
                                    if not self.client_side
                                    else {
                                        "type": "button",
                                        "@click": f"activeTab = '{value}'",
                                        "x_bind__class": f"activeTab === '{value}' ? 'bg-background text-foreground shadow' : 'text-muted-foreground hover:text-foreground'",
                                        "role": "tab",
                                        "aria_selected": "true" if value == self.active_id else "false",
                                        "aria_controls": f"tabpanel-{value}",
                                        "id": f"tab-{value}",
                                    }
                                ),
                            )
                            for label, value in self.tabs
                        ],
                        class_="inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
                        role="tablist",
                        aria_label="Tabs",
                        **keyboard_nav,
                    ),
                    class_="hidden sm:block mb-6",
                ),
            # Content container (for children like TabPanel)
            el("div", *self.children, class_="mt-4"),
            **attrs,
        )


class TabPanel(Component):
    """
    Wrapper for tab content.
    Automatically shows/hides based on the parent Tabs' state.
    """

    def __init__(self, tab_id: str, *children, **props) -> None:
        super().__init__(*children, **props)
        self.id = tab_id

    def render(self) -> Any:
        return el(
            "div",
            *self.children,
            role="tabpanel",
            aria_labelledby=f"tab-{self.id}",
            id=f"tabpanel-{self.id}",
            x_show=f"activeTab === '{self.id}'",
            x_cloak="true",
            class_="tab-panel",
        )
