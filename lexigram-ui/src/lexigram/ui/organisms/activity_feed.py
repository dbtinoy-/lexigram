from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class ActivityFeed(Component):
    def __init__(
        self,
        title: str = "Recent Activity",
        items: list[dict[str, Any]] | None = None,
        max_items: int = 5,
        **props,
    ) -> None:
        super().__init__(title=title, items=items or [], max_items=max_items, **props)
        self.title = title
        self.items = items or []
        self.max_items = max_items

    def render(self) -> Any:
        activity_items: list[Any] = []

        for item in self.items[: self.max_items]:
            user = item.get("user", "System")
            action = item.get("action", "performed action")
            resource = item.get("resource", "")
            timestamp = item.get("timestamp", "just now")
            icon = item.get("icon", "•")

            activity_item = el(
                "li",
                el(
                    "div",
                    el("span", icon, class_="text-primary mr-2"),
                    el(
                        "span",
                        el(
                            "strong",
                            user,
                            class_="font-medium text-foreground",
                        ),
                        f" {action} ",
                        el("span", resource, class_="text-primary font-medium")
                        if resource
                        else "",
                        class_="text-sm text-muted-foreground",
                    ),
                    class_="flex items-start",
                ),
                el(
                    "span",
                    timestamp,
                    class_="text-xs text-muted-foreground ml-6",
                ),
                class_="py-3 border-b border-border last:border-0",
            )
            activity_items.append(activity_item)

        if not activity_items:
            activity_items.append(
                el(
                    "li",
                    el(
                        "p",
                        "No recent activity",
                        class_="text-sm text-muted-foreground text-center",
                    ),
                    class_="py-8",
                )
            )

        return el(
            "div",
            el(
                "h3",
                self.title,
                class_="text-lg font-semibold text-foreground mb-4 px-6 pt-6",
            ),
            el("ul", *activity_items, class_="px-6 pb-6"),
            class_="bg-card rounded-xl shadow-sm border border-border transition-colors duration-300",
        )
