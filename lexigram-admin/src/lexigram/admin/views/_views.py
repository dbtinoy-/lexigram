"""Alternative resource list view implementations — Calendar, Kanban, Tree.

EXPERIMENTAL: These view types are paused. See the follow-up Filament
evolution plan for the path forward (Page abstraction).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

from lexigram.ui import el, render_to_string


class ResourceView(Protocol):
    """Protocol for alternative resource list views."""

    def render(self, records: list[dict[str, Any]]) -> str:
        """Render the view to an HTML string.

        Args:
            records: List of resource record dicts.

        Returns:
            HTML fragment ready for insertion into the admin layout.
        """
        ...

    @property
    def view_type(self) -> str:
        """Machine-readable view type identifier."""
        ...


@dataclass
class CalendarView:
    """Groups resource records onto a monthly calendar grid.

    Args:
        date_field: Field containing the date/datetime for placement.
        title_field: Field used as the card label.
        month: Target month (1-12).  Defaults to current month.
        year: Target year.  Defaults to current year.
        css_class: Extra CSS class applied to the calendar container.
    """

    date_field: str = "created_at"
    title_field: str = "name"
    month: int = field(default_factory=lambda: date.today().month)
    year: int = field(default_factory=lambda: date.today().year)
    css_class: str = ""

    view_type: str = "calendar"

    def _parse_date(self, value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value[:19], fmt).date()
                except ValueError:
                    pass
            # Last resort: try just the date portion
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        return None

    def _days_in_month(self) -> int:
        import calendar as cal

        return cal.monthrange(self.year, self.month)[1]

    def _first_weekday(self) -> int:
        """Return weekday of the 1st (Monday=0, Sunday=6)."""
        return date(self.year, self.month, 1).weekday()

    def group_by_day(
        self, records: list[dict[str, Any]]
    ) -> dict[int, list[dict[str, Any]]]:
        """Group records by day-of-month for this calendar's month/year.

        Args:
            records: Resource records to group.

        Returns:
            Dict mapping day number (1-31) → list of matching records.
        """
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            raw = record.get(self.date_field)
            d = self._parse_date(raw)
            if d and d.year == self.year and d.month == self.month:
                grouped[d.day].append(record)
        return dict(grouped)

    def render(self, records: list[dict[str, Any]]) -> str:
        """Render records onto a monthly calendar grid.

        Args:
            records: Resource records.

        Returns:
            HTML fragment with a month calendar grid.
        """
        grouped = self.group_by_day(records)
        days_in_month = self._days_in_month()
        first_weekday = self._first_weekday()  # Monday=0

        month_name = date(self.year, self.month, 1).strftime("%B %Y")
        day_headers = [
            el("th", d, class_="cal-header")
            for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        ]

        cells: list[Any] = [el("td") for _ in range(first_weekday)]
        for day in range(1, days_in_month + 1):
            day_records = grouped.get(day, [])
            events = [
                el("div", r.get(self.title_field, r.get("id", "")), class_="cal-event")
                for r in day_records
            ]
            day_num_span = el("span", str(day), class_="cal-day-num")
            cells.append(el("td", day_num_span, *events, class_="cal-day"))

        # Pad to complete last row
        remainder = (first_weekday + days_in_month) % 7
        if remainder:
            cells.extend([el("td") for _ in range(7 - remainder)])

        rows = []
        for i in range(0, len(cells), 7):
            row_cells = cells[i : i + 7]
            rows.append(el("tr", *row_cells))

        extra = f" {self.css_class}" if self.css_class else ""
        return render_to_string(
            el(
                "div",
                el("div", month_name, class_="cal-title"),
                el(
                    "table",
                    el("thead", el("tr", *day_headers)),
                    el("tbody", *rows),
                    class_="cal-table",
                ),
                class_=f"admin-calendar-view{extra}",
            )
        )


@dataclass
class KanbanView:
    """Groups resource records into status-based kanban columns.

    Args:
        status_field: Field used to determine which column a record belongs to.
        columns: Ordered list of status values / column names.
        title_field: Field used as the card label.
        subtitle_field: Optional field shown as a subtitle on the card.
        css_class: Extra CSS class applied to the board container.
    """

    status_field: str = "status"
    columns: list[str] = field(default_factory=lambda: ["todo", "in_progress", "done"])
    title_field: str = "name"
    subtitle_field: str = ""
    css_class: str = ""

    view_type: str = "kanban"

    def group_by_status(
        self, records: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group records by their status value.

        Records whose status is not in :attr:`columns` are placed in an
        ``"_other"`` bucket.

        Args:
            records: Resource records.

        Returns:
            Dict mapping status → list of records.
        """
        grouped: dict[str, list[dict[str, Any]]] = {col: [] for col in self.columns}
        grouped["_other"] = []
        for record in records:
            status = str(record.get(self.status_field, ""))
            if status in grouped:
                grouped[status].append(record)
            else:
                grouped["_other"].append(record)
        return grouped

    def render(self, records: list[dict[str, Any]]) -> str:
        """Render records as a kanban board.

        Args:
            records: Resource records.

        Returns:
            HTML fragment with draggable column cards (Alpine/HTMX ready).
        """
        grouped = self.group_by_status(records)

        columns: list[Any] = []
        for col in self.columns:
            col_records = grouped.get(col, [])
            cards: list[Any] = []
            for record in col_records:
                title = record.get(self.title_field, record.get("id", ""))
                subtitle = (
                    record.get(self.subtitle_field, "") if self.subtitle_field else ""
                )
                record_id = record.get("id", "")
                subtitle_el = (
                    el("p", subtitle, class_="kanban-subtitle") if subtitle else None
                )
                card_children: list[Any] = [
                    el("div", title, class_="kanban-card-title")
                ]
                if subtitle_el is not None:
                    card_children.append(subtitle_el)
                cards.append(
                    el(
                        "div",
                        *card_children,
                        **{
                            "class": "kanban-card",
                            "data-id": str(record_id),
                            "draggable": "true",
                        },
                    )
                )

            col_label = col.replace("_", " ").title()
            columns.append(
                el(
                    "div",
                    el(
                        "div",
                        f"{col_label} ",
                        el("span", str(len(col_records)), class_="kanban-count"),
                        class_="kanban-col-header",
                    ),
                    el("div", *cards, class_="kanban-cards"),
                    **{
                        "class": "kanban-column",
                        "data-status": col,
                        "hx-post": "",
                        "hx-trigger": "drop",
                    },
                )
            )

        extra = f" {self.css_class}" if self.css_class else ""
        return render_to_string(
            el(
                "div",
                *columns,
                **{"class": f"admin-kanban-view{extra}", "x-data": "kanbanBoard()"},
            )
        )


@dataclass
class TreeView:
    """Renders resource records as a collapsible parent/child tree.

    Args:
        id_field: Field containing the record's unique ID.
        parent_field: Field containing the parent record's ID (``None`` for
            root nodes).
        label_field: Field used as the node label.
        css_class: Extra CSS class applied to the tree container.
    """

    id_field: str = "id"
    parent_field: str = "parent_id"
    label_field: str = "name"
    css_class: str = ""

    view_type: str = "tree"

    def build_tree(
        self, records: list[dict[str, Any]]
    ) -> dict[Any, list[dict[str, Any]]]:
        """Build a parent → children mapping from flat records.

        Args:
            records: Flat list of resource records.

        Returns:
            Dict mapping parent_id → list of direct children.  Root nodes
            are stored under the key ``None``.
        """
        children: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            parent_id = record.get(self.parent_field)
            children[parent_id].append(record)
        return dict(children)

    def _render_nodes(
        self,
        children_map: dict[Any, list[dict[str, Any]]],
        parent_id: Any,
        depth: int = 0,
    ) -> list[Any]:
        nodes = children_map.get(parent_id, [])
        if not nodes:
            return []

        result: list[Any] = []
        for node in nodes:
            node_id = node.get(self.id_field, "")
            label = node.get(self.label_field, str(node_id))
            has_children = node_id in children_map
            toggle_attrs: dict[str, Any] = {}
            if has_children:
                toggle_attrs = {"x-data": "{open: true}", "@click": "open = !open"}
            child_nodes = self._render_nodes(children_map, node_id, depth + 1)
            children_ul = (
                el("ul", *child_nodes, class_="tree-children") if child_nodes else None
            )
            label_el = el("div", label, class_="tree-node-label", **toggle_attrs)
            li_children: list[Any] = [label_el]
            if children_ul:
                li_children.append(children_ul)
            result.append(
                el(
                    "li",
                    *li_children,
                    **{
                        "class": "tree-node",
                        "data-id": str(node_id),
                        "data-depth": str(depth),
                    },
                )
            )
        return result

    def render(self, records: list[dict[str, Any]]) -> str:
        """Render records as a collapsible tree.

        Args:
            records: Resource records.

        Returns:
            HTML fragment with a nested ``<ul>`` tree (Alpine ``x-data`` for
            collapse/expand).
        """
        children_map = self.build_tree(records)
        root_nodes = self._render_nodes(children_map, None)

        extra = f" {self.css_class}" if self.css_class else ""
        return render_to_string(
            el(
                "div",
                el("ul", *root_nodes, class_="tree-root"),
                class_=f"admin-tree-view{extra}",
            )
        )


@dataclass
class AuditLogView:
    """Renders audit log entries as a timeline of user actions.

    Args:
        user_field: Field for the user/actor name.
        action_field: Field for the action description.
        timestamp_field: Field for the event timestamp.
        css_class: Extra CSS class on container.
    """

    user_field: str = "user"
    action_field: str = "action"
    timestamp_field: str = "created_at"
    css_class: str = ""
    view_type: str = "audit_log"

    def render(self, records: list[dict[str, Any]]) -> str:
        """Render audit log entries as a ``<ul class="audit-timeline">`` list.

        Each entry contains a timestamp badge, a user avatar initial, and the
        action text.

        Args:
            records: List of audit-log record dicts.

        Returns:
            HTML fragment ready for insertion into the admin layout.
        """
        items: list[Any] = []
        for record in records:
            timestamp = str(record.get(self.timestamp_field, ""))
            user = str(record.get(self.user_field, "?"))
            action = str(record.get(self.action_field, ""))

            # Derive initials for the avatar (first letter of first word)
            avatar_letter = user[0].upper() if user else "?"

            timestamp_badge = el(
                "span",
                timestamp,
                class_="audit-timestamp text-xs text-muted-foreground tabular-nums",
            )
            avatar = el(
                "span",
                avatar_letter,
                class_=(
                    "audit-avatar inline-flex items-center justify-center "
                    "w-7 h-7 rounded-full bg-primary-100 dark:bg-primary-900 "
                    "text-primary-700 dark:text-primary-300 text-xs font-semibold "
                    "shrink-0"
                ),
                title=user,
            )
            action_text = el(
                "span",
                action,
                class_="audit-action text-sm text-foreground",
            )
            entry_inner = el(
                "div",
                avatar,
                el(
                    "div",
                    action_text,
                    timestamp_badge,
                    class_="flex flex-col gap-0.5",
                ),
                class_="flex items-start gap-2",
            )
            items.append(el("li", entry_inner, class_="audit-entry py-2"))

        extra = f" {self.css_class}" if self.css_class else ""
        return render_to_string(
            el(
                "ul",
                *items,
                class_=f"audit-timeline divide-y divide-border{extra}",
            )
        )


@dataclass
class UserImpersonationView:
    """Renders a user selection table for impersonation.

    Args:
        id_field: Field for the user's ID.
        name_field: Field for the user's display name.
        email_field: Field for the user's email.
        impersonate_url_prefix: URL prefix for impersonation endpoint.
        css_class: Extra CSS class.
    """

    id_field: str = "id"
    name_field: str = "name"
    email_field: str = "email"
    impersonate_url_prefix: str = "/admin/impersonate"
    css_class: str = ""
    view_type: str = "user_impersonation"

    def render(self, records: list[dict[str, Any]]) -> str:
        """Render a table of users with an "Impersonate" action per row.

        The impersonate button sends an HTMX POST to
        ``{impersonate_url_prefix}/{user_id}`` with an ``hx-confirm`` prompt.

        Args:
            records: List of user record dicts.

        Returns:
            HTML fragment containing the impersonation table.
        """
        header_row = el(
            "tr",
            el(
                "th",
                "Name",
                class_="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-foreground uppercase tracking-wider",
            ),
            el(
                "th",
                "Email",
                class_="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-foreground uppercase tracking-wider",
            ),
            el(
                "th",
                "Action",
                class_="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-foreground uppercase tracking-wider",
            ),
        )

        rows: list[Any] = []
        for record in records:
            user_id = str(record.get(self.id_field, ""))
            name = str(record.get(self.name_field, user_id))
            email = str(record.get(self.email_field, ""))
            impersonate_url = f"{self.impersonate_url_prefix.rstrip('/')}/{user_id}"

            button = el(
                "button",
                "Impersonate",
                type="button",
                class_=(
                    "inline-flex items-center px-3 py-1.5 text-xs font-medium "
                    "text-white bg-primary-600 hover:bg-primary-700 rounded-md "
                    "focus:outline-none focus:ring-2 focus:ring-primary-500 "
                    "transition-colors"
                ),
                **{
                    "hx-post": impersonate_url,
                    "hx-target": "body",
                    "hx-swap": "none",
                    "hx-confirm": f"Impersonate {name}?",
                },
            )

            rows.append(
                el(
                    "tr",
                    el(
                        "td",
                        name,
                        class_="px-4 py-3 text-sm text-foreground",
                    ),
                    el(
                        "td",
                        email,
                        class_="px-4 py-3 text-sm text-muted-foreground",
                    ),
                    el("td", button, class_="px-4 py-3"),
                    class_="border-t border-border hover:bg-muted dark:hover:bg-muted/50",
                )
            )

        extra = f" {self.css_class}" if self.css_class else ""
        return render_to_string(
            el(
                "div",
                el(
                    "table",
                    el("thead", header_row, class_="bg-muted"),
                    el("tbody", *rows),
                    class_="w-full border-collapse text-sm",
                ),
                class_=f"admin-impersonation-view overflow-x-auto rounded-lg border border-border{extra}",
            )
        )


__all__ = [
    "AuditLogView",
    "CalendarView",
    "KanbanView",
    "ResourceView",
    "TreeView",
    "UserImpersonationView",
]
