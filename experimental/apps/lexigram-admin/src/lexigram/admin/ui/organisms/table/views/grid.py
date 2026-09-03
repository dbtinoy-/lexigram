from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.data_table.actions import render_action_button
from lexigram.admin.ui.organisms.table.views.tabular import AbstractDataView
from lexigram.admin.ui.organisms.table.views.tabular_rows import (
    extract_row_id,
    get_attr,
)
from lexigram.ui import Checkbox, InfiniteScrollTrigger, Zones, el


class GridView(AbstractDataView):
    """Render data as a Grid of Cards."""

    def render(self) -> Any:
        cards = []
        for _, item in enumerate(self.data):
            extracted_id = extract_row_id(item)
            has_row_id = bool(extracted_id)
            rid = extracted_id or f"row-{_}"
            # Smart Field Detection
            image = (
                get_attr(item, "image_url")
                or get_attr(item, "image")
                or get_attr(item, "avatar")
                or get_attr(item, "cover")
                or ""
            )
            title = (
                get_attr(item, "name")
                or get_attr(item, "title")
                or get_attr(item, "label")
                or f"ID: {rid}"
            )

            # Subtitle construction
            subtitle_parts = []
            for k in ["species", "breed", "category", "email", "status"]:
                if val := get_attr(item, k):
                    subtitle_parts.append(str(val))
            subtitle = " • ".join(subtitle_parts[:2])  # Max 2 items

            # Grid Actions (Selection + Row Actions)
            action_nodes = []
            if self.config.resource_prefix:
                # Checkbox
                if self.config.bulk_actions and has_row_id:
                    action_nodes.append(
                        Checkbox(
                            name="ids",
                            id=f"grid-select-{rid}",
                            value=rid,
                            x_model="selectedIds",
                            class_="absolute top-2 left-2 z-10",
                            aria_label=f"Select {rid}",
                        )
                    )

                # Row Actions require a real record id; a synthetic display
                # id must never become a destructive/action URL.
                if not has_row_id:
                    action_nodes = []
                for action in self.config.actions if has_row_id else ():
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
                        form_display_mode=getattr(
                            self.config, "form_display_mode", None
                        ),
                    )
                    if node:
                        action_nodes.append(node)

            actions_overlay = (
                el(
                    "div",
                    *action_nodes,
                    class_="absolute top-2 right-2 z-10 flex flex-col items-end gap-2",
                )
                if action_nodes
                else ""
            )

            detail_href = (
                f"{self.config.resource_prefix}/{rid}"
                if self.config.resource_prefix
                else "#"
            )

            card = el(
                "div",
                actions_overlay,
                el(
                    "div",
                    el(
                        "img",
                        src=image,
                        alt=title,
                        loading="lazy",
                        class_="w-full h-40 object-cover",
                    )
                    if image
                    else el(
                        "div",
                        str(title)[0].upper(),
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
                        "View details",
                        href=detail_href,
                        class_="text-sm text-primary-600 hover:text-primary-700 font-medium",
                    )
                    if self.config.resource_prefix and has_row_id
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

        # Select-all bar for bulk operations
        select_all_bar = self.render_select_all_bar()

        # Only show trigger if we have a next cursor (more data to load)
        next_cursor = (
            self.next_cursor
            or getattr(self.state, "next_cursor", None)
            or getattr(self.config, "next_cursor", None)
        )

        if next_cursor and self.config.resource_prefix:
            from urllib.parse import urlencode

            params = {**self.state.to_query_params(), "cursor": next_cursor}
            next_url = f"{self.config.resource_prefix}/?{urlencode(params, doseq=True)}"

            trigger = InfiniteScrollTrigger(
                url=next_url,
                target=f"#{Zones.DATA.id}",  # Target the content container
                swap="beforeend",
            )
            return el("div", select_all_bar, grid, trigger.render())

        return el("div", select_all_bar, grid) if select_all_bar else grid
