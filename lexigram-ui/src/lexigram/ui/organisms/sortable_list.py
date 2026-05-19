"""Sortable / drag-n-drop record reorder component.

Provides :class:`SortableRecordList` — a table that lets users drag rows
into a new order and persists the new order via an HTMX PATCH request
(FilamentPHP: Y, Django Admin: E).

Usage::

    rows = [
        {"id": 1, "title": "First post"},
        {"id": 2, "title": "Second post"},
    ]
    widget = SortableRecordList(
        rows=rows,
        id_field="id",
        label_field="title",
        reorder_url="/admin/posts/reorder",
    )
    html = widget.render()

The client-side uses SortableJS (loaded via CDN) and an Alpine.js controller
that fires an HTMX PATCH to *reorder_url* with a JSON body::

    {"order": [2, 1]}
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class SortableRecordList(Component):
    """Drag-n-drop sortable list for reordering records.

    Args:
        rows: Sequence of record dicts (or objects with ``__getitem__``).
        id_field: Key used to identify each record (default ``"id"``).
        label_field: Key used as the visible label (default ``"title"``).
        reorder_url: URL for the HTMX PATCH request carrying the new order.
        hx_target: HTMX swap target (default ``"this"``).
        hx_swap: HTMX swap strategy (default ``"none"``).
        handle_class: CSS class to add to the drag handle icon.
        empty_label: Text shown when *rows* is empty.
    """

    def __init__(
        self,
        rows: list[Any],
        id_field: str = "id",
        label_field: str = "title",
        reorder_url: str = "",
        hx_target: str = "this",
        hx_swap: str = "none",
        handle_class: str = "",
        empty_label: str = "No records to reorder.",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.rows = rows
        self.id_field = id_field
        self.label_field = label_field
        self.reorder_url = reorder_url
        self.hx_target = hx_target
        self.hx_swap = hx_swap
        self.handle_class = handle_class
        self.empty_label = empty_label

    # ------------------------------------------------------------------

    def render(self) -> Any:
        if not self.rows:
            return el(
                "div",
                self.empty_label,
                class_=(
                    "flex items-center justify-center h-20 "
                    "text-sm text-muted-foreground dark:text-muted-foreground "
                    "border border-dashed border-border rounded-lg"
                ),
            )

        row_els = [self._row_el(row, idx) for idx, row in enumerate(self.rows)]
        list_el = el(
            "ul",
            *row_els,
            id="sortable-list",
            class_=(
                "divide-y divide-border rounded-lg border border-border overflow-hidden"
            ),
            **{"x-ref": "sortableList"},
        )

        # Save button — fires HTMX PATCH with current order
        save_btn = el(
            "button",
            "Save order",
            type="button",
            class_=(
                "mt-3 inline-flex items-center px-4 py-2 text-sm font-medium rounded-md "
                "bg-primary text-primary-foreground hover:bg-primary/90 "
                "disabled:opacity-50 transition-colors"
            ),
            **{
                "@click": "saveOrder()",
                "hx-patch": self.reorder_url,
                "hx-target": self.hx_target,
                "hx-swap": self.hx_swap,
                "hx-ext": "json-enc",
                "x-bind:disabled": "!dirty",
                ":class": "{'opacity-50 cursor-not-allowed': !dirty}",
            },
        )

        # Alpine.js controller that initialises SortableJS and tracks changes
        alpine_init = self._alpine_script()

        return el(
            "div",
            alpine_init,
            list_el,
            save_btn,
            **{
                "x-data": "sortableRecords()",
                "x-init": "init()",
                "class": "space-y-2",
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_el(self, row: Any, idx: int) -> Any:
        record_id = self._get(row, self.id_field, str(idx))
        label = self._get(row, self.label_field, f"Record {idx + 1}")
        handle_cls = f"cursor-grab active:cursor-grabbing text-muted-foreground mr-3 {self.handle_class}".strip()
        handle = el("span", "⠿", class_=handle_cls, **{"aria-hidden": "true"})
        label_el = el(
            "span",
            str(label),
            class_="text-sm text-foreground",
        )
        return el(
            "li",
            handle,
            label_el,
            **{
                "data-id": str(record_id),
                "class": (
                    "flex items-center px-4 py-3 "
                    "bg-card "
                    "hover:bg-muted dark:hover:bg-muted "
                    "select-none"
                ),
            },
        )

    @staticmethod
    def _get(row: Any, key: str, default: Any = "") -> Any:
        if isinstance(row, dict):
            return row.get(key, default)
        return getattr(row, key, default)

    def _alpine_script(self) -> Any:
        """Render the inline Alpine.js + SortableJS setup script."""
        js = (
            "function sortableRecords() {"
            "  return {"
            "    dirty: false,"
            "    sortable: null,"
            "    init() {"
            "      if (typeof Sortable === 'undefined') return;"
            "      this.sortable = new Sortable(this.$refs.sortableList, {"
            "        animation: 150,"
            "        handle: 'span[aria-hidden]',"
            "        onEnd: () => { this.dirty = true; }"
            "      });"
            "    },"
            "    saveOrder() {"
            "      const items = this.$refs.sortableList.querySelectorAll('li');"
            "      const order = Array.from(items).map(el => el.dataset.id);"
            "      htmx.ajax('PATCH', '" + self.reorder_url + "', {"
            "        target: '" + self.hx_target + "',"
            "        swap: '" + self.hx_swap + "',"
            "        values: { order: order }"
            "      });"
            "      this.dirty = false;"
            "    }"
            "  };"
            "}"
        )
        return el("script", js, type="text/javascript")
