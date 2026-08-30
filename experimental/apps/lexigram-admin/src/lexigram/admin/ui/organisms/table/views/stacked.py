from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.data_table.actions import render_action_button
from lexigram.admin.ui.organisms.table.views.tabular import AbstractDataView
from lexigram.admin.ui.organisms.table.views.tabular_rows import (
    extract_row_id,
    get_attr,
)
from lexigram.ui import Checkbox, el


class StackedView(AbstractDataView):
    """Render data as a stacked list of field-value pairs (ideal for mobile)."""

    def render(self) -> Any:
        cards = []
        for _, item in enumerate(self.data):
            extracted_id = extract_row_id(item)
            has_row_id = bool(extracted_id)
            rid = extracted_id or f"row-{_}"
            # Row Header (Checkbox + Title + Actions)
            header_parts = []

            if self.config.resource_prefix and self.config.bulk_actions and has_row_id:
                header_parts.append(
                    el(
                        "div",
                        Checkbox(
                            name="ids",
                            value=rid,
                            x_model="selectedIds",
                            aria_label=f"Select {rid}",
                        ),
                        class_="flex-shrink-0",
                    ),
                )

            # Detect Primary Field for the card header
            primary_val = (
                get_attr(item, "name")
                or get_attr(item, "title")
                or get_attr(item, "label")
                or f"Record {rid}"
            )
            header_parts.append(
                el(
                    "div",
                    el(
                        "span",
                        primary_val,
                        class_="font-bold text-foreground truncate",
                    ),
                    class_="flex-1 min-w-0",
                ),
            )

            # Row Actions
            if self.config.resource_prefix and has_row_id:
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
                        form_display_mode=getattr(
                            self.config, "form_display_mode", None
                        ),
                    )
                    if node:
                        action_nodes.append(node)

                # Stack action buttons vertically inside the card header
                header_parts.append(
                    el(
                        "div",
                        *action_nodes,
                        class_="flex flex-col items-start gap-1 flex-shrink-0",
                    ),
                )

            card_header = el(
                "div",
                *header_parts,
                class_="flex items-center gap-3 p-4 border-b border-border bg-muted/50 dark:bg-card/50",
            )

            # Field List
            fields = []
            for col in self.config.columns:
                if not col.is_visible(
                    user=self.user,
                    resource_name=self.resource_name,
                    record=item,
                ):
                    continue

                val = col.get_value(item)
                rendered_val = col.render(col.format_value(val), item)

                fields.append(
                    el(
                        "div",
                        el(
                            "dt",
                            col.label,
                            class_="text-xs font-medium text-muted-foreground uppercase tracking-wider w-1/3 flex-shrink-0",
                        ),
                        el(
                            "dd",
                            rendered_val,
                            class_="text-sm text-foreground flex-1 min-w-0",
                        ),
                        class_="flex items-start gap-4 py-2 px-4 border-b border-border last:border-0",
                    ),
                )

            card_body = el(
                "dl",
                *fields,
                class_="divide-y divide-border",
            )

            card = el(
                "div",
                card_header,
                card_body,
                class_="bg-card rounded-xl border border-border shadow-sm overflow-hidden mb-4 last:mb-0",
            )
            cards.append(card)

        stack = el("div", *cards, class_="block space-y-4")

        # Select-all bar for bulk operations
        select_all_bar = self.render_select_all_bar()

        # Virtual Scroll Logic
        next_cursor = (
            self.next_cursor
            or getattr(self.state, "next_cursor", None)
            or getattr(self.config, "next_cursor", None)
        )

        if next_cursor and self.config.resource_prefix:
            from urllib.parse import urlencode

            from lexigram.ui import InfiniteScrollTrigger, Zones

            params = {**self.state.to_query_params(), "cursor": next_cursor}
            next_url = f"{self.config.resource_prefix}/?{urlencode(params, doseq=True)}"

            trigger = InfiniteScrollTrigger(
                url=next_url,
                target=f"#{Zones.DATA.id}",
                swap="beforeend",
            )
            return el("div", select_all_bar, stack, trigger.render())

        return el("div", select_all_bar, stack) if select_all_bar else stack
