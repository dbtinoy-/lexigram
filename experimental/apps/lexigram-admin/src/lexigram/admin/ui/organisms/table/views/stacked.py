from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.data_table.actions import render_action_button
from lexigram.admin.ui.organisms.table.views.tabular import AbstractDataView
from lexigram.ui import Checkbox, el


def _get_attr(item: Any, key: str, default: Any = None) -> Any:
    """Safely get attribute from dict or Pydantic model."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


class StackedView(AbstractDataView):
    """Render data as a stacked list of field-value pairs (ideal for mobile)."""

    def render(self) -> Any:
        cards = []
        for _, item in enumerate(self.data):
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
            # Row Header (Checkbox + Title + Actions)
            header_parts = []

            if self.config.resource_prefix and self.config.bulk_actions:
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
                _get_attr(item, "name")
                or _get_attr(item, "title")
                or _get_attr(item, "label")
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
            if self.config.resource_prefix:
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

        # Virtual Scroll Logic
        next_cursor = getattr(self.state, "next_cursor", None) or getattr(
            self.config,
            "next_cursor",
            None,
        )
        if not next_cursor and hasattr(self, "next_cursor"):
            next_cursor = self.next_cursor

        if next_cursor and self.config.resource_prefix:
            from urllib.parse import urlencode

            from lexigram.ui import InfiniteScrollTrigger, Zones

            params = {**self.state.to_query_params(), "cursor": next_cursor}
            next_url = f"{self.config.resource_prefix}/?{urlencode(params)}"

            trigger = InfiniteScrollTrigger(
                url=next_url,
                target=f"#{Zones.DATA.id}",
                swap="beforeend",
            )
            return el("div", stack, trigger.render())

        return stack
