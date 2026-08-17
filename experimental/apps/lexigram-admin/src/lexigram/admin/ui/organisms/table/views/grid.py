from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.data_table.actions import render_action_button
from lexigram.admin.ui.organisms.table.views.tabular import AbstractDataView
from lexigram.ui import Checkbox, InfiniteScrollTrigger, Zones, el


def _get_attr(item: Any, key: str, default: Any = None) -> Any:
    """Safely get attribute from dict or Pydantic model."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


class GridView(AbstractDataView):
    """Render data as a Grid of Cards."""

    def render(self) -> Any:
        cards = []
        for _, item in enumerate(self.data):
            # Get ID safely for both dict and Pydantic model
            rid = ""
            if isinstance(item, dict):
                rid = str(item.get("id", item.get("user_id", item.get("pk", ""))))
            elif hasattr(item, "id"):
                rid = str(item.id)
            elif hasattr(item, "user_id"):
                rid = str(item.user_id)
            elif hasattr(item, "pk"):
                rid = str(item.pk)
            elif hasattr(item, "__getitem__"):
                try:
                    rid = str(item[0])
                except (IndexError, TypeError):
                    rid = ""

            # If rid is still empty, fallback to a safe string
            if not rid:
                rid = f"row-{_}"
            # Smart Field Detection
            image = (
                _get_attr(item, "image_url")
                or _get_attr(item, "image")
                or _get_attr(item, "avatar")
                or _get_attr(item, "cover")
                or ""
            )
            title = (
                _get_attr(item, "name")
                or _get_attr(item, "title")
                or _get_attr(item, "label")
                or f"ID: {rid}"
            )

            # Subtitle construction
            subtitle_parts = []
            for k in ["species", "breed", "category", "email", "status"]:
                if val := _get_attr(item, k):
                    subtitle_parts.append(str(val))
            subtitle = " • ".join(subtitle_parts[:2])  # Max 2 items

            # Grid Actions (Selection + Row Actions)
            actions_overlay = ""
            if self.config.resource_prefix:
                # Checkbox
                checkbox = (
                    Checkbox(
                        name="ids",
                        value=rid,
                        x_model="selectedIds",
                        class_="absolute top-2 left-2 z-10",
                        aria_label=f"Select {rid}",
                    )
                    if self.config.bulk_actions
                    else ""
                )

                # Row Actions (Optional: show primary action or menu)
                action_nodes = []
                for action in self.config.actions:
                    if not action.is_visible(
                        user=self.user,
                        resource_name=self.resource_name,
                        record=item,
                    ):
                        continue
                    node = render_action_button(
                        action,
                        record=item,
                        user=self.user,
                        resource_name=self.resource_name,
                        resource_prefix=self.config.resource_prefix,
                    )
                    if node:
                        action_nodes.append(node)

                actions_overlay = el("div", checkbox, *action_nodes)

                card = el(
                    "div",
                    actions_overlay,
                    el(
                        "div",
                        el("img", src=image, alt="", class_="w-full h-40 object-cover")
                        if image
                        else el(
                            "div",
                            title[0].upper(),
                            aria_hidden="true",
                            class_="w-full h-40 bg-muted dark:bg-card flex items-center justify-center text-4xl text-foreground font-bold",
                        ),
                        class_="relative",
                    ),
                    el(
                        "div",
                        el("h3", title, class_="font-semibold text-lg mb-1 truncate"),
                        el(
                            "p",
                            subtitle,
                            class_="text-sm text-muted-foreground mb-4 h-5 overflow-hidden",
                        ),
                        el(
                            "a",
                            "View Details",
                            href=f"{self.config.resource_prefix}/{rid}/edit"
                            if self.config.resource_prefix
                            else "#",
                            class_="text-sm text-primary-600 hover:text-primary-700 font-medium",
                        )
                        if self.config.resource_prefix
                        else "",
                        class_="p-4",
                    ),
                    class_="bg-card rounded-xl border border-border shadow-sm hover:shadow-md transition-shadow overflow-hidden relative group",
                )
            cards.append(card)

        grid = el(
            "div",
            *cards,
            class_="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6",
        )

        # Only show trigger if we have a next cursor (more data to load)
        next_cursor = getattr(self.state, "next_cursor", None) or getattr(
            self.config,
            "next_cursor",
            None,
        )

        # In case the parent passed it as a prop (standard in DataTable)
        if not next_cursor and hasattr(self, "next_cursor"):
            next_cursor = self.next_cursor

        if next_cursor and self.config.resource_prefix:
            from urllib.parse import urlencode

            params = {**self.state.to_query_params(), "cursor": next_cursor}
            next_url = f"{self.config.resource_prefix}/?{urlencode(params)}"

            trigger = InfiniteScrollTrigger(
                url=next_url,
                target=f"#{Zones.DATA.id}",  # Target the content container
                swap="beforeend",
            )
            return el("div", grid, trigger.render())

        return grid
