from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Breadcrumbs(Component):
    """
    Breadcrumb navigation component with home icon.

    Args:
        items: List of dicts with 'label' and 'url'
    """

    def __init__(self, items: list[dict[str, str]], **props) -> None:
        super().__init__(**props)
        self.items = items

    def render(self) -> Any:
        from lexigram.ui.atoms.icons import get_icon

        return el(
            "nav",
            {"class": "flex", "aria-label": "Breadcrumb"},
            el(
                "ol",
                {"class": "flex items-center space-x-4"},
                # Home Icon
                el(
                    "li",
                    el(
                        "div",
                        el(
                            "a",
                            get_icon(
                                "home",
                                class_name="h-5 w-5 flex-shrink-0",
                                aria_hidden="true",
                            ),
                            href="/admin",
                            class_="text-muted-foreground hover:text-foreground transition-colors",
                        ),
                    ),
                ),
                # Breadcrumb Items
                *[
                    el(
                        "li",
                        el(
                            "div",
                            {"class": "flex items-center"},
                            get_icon(
                                "chevron-right",
                                class_name="h-5 w-5 flex-shrink-0 text-muted-foreground",
                                aria_hidden="true",
                            ),
                            el(
                                "a",
                                item["label"],
                                href=item.get("url", "#"),
                                class_=f"ml-4 text-sm font-medium transition-colors {'text-muted-foreground hover:text-foreground' if i < len(self.items) - 1 else 'text-foreground cursor-default'}",
                                # Only add hx attributes if it's a link and not the last item
                                **(
                                    {
                                        "hx_get": item.get("url"),
                                        "hx_target": "#main-content",
                                        "hx_swap": "innerHTML",
                                        "hx_push_url": "true",
                                    }
                                    if i < len(self.items) - 1 and item.get("url")
                                    else {}
                                ),
                            ),
                        ),
                    )
                    for i, item in enumerate(self.items)
                ],
            ),
        )
