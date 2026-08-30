"""Per-``data_view`` toolbar and chrome capability map.

The four resource-table view strategies (``tabular``, ``stacked``, ``grid``,
``calendar``) are the highest-order structure of a list page. Search, filters,
header actions, row actions and bulk actions stay available on every view;
presentation controls that only make sense for a given strategy are gated
here so the toolbar never offers a dead button.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

DataView = Literal["tabular", "stacked", "grid", "calendar"]

DATA_VIEWS: Final[tuple[DataView, ...]] = (
    "tabular",
    "stacked",
    "grid",
    "calendar",
)

DATA_VIEW_OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("tabular", "Tabular"),
    ("stacked", "Stacked"),
    ("grid", "Grid"),
    ("calendar", "Calendar"),
)


@dataclass(frozen=True)
class ViewControls:
    """Which table chrome a ``data_view`` may render.

    Attributes:
        search: Toolbar search input.
        filters: Filter bar.
        header_actions: Create / import and other top actions.
        row_actions: Per-record view/edit/delete buttons.
        bulk_actions: Selection checkboxes and bulk action bar.
        column_sort: Sortable column headers (tabular only).
        toolbar_sort: Sort dropdown for views without column headers.
        density: Row-density segmented control (tabular row height).
        column_visibility: Show/hide columns (views that render fields).
        group_by: Group-by dropdown (tabular grouping headers).
        layout: Stack vs sidebar chrome switcher.
    """

    search: bool = True
    filters: bool = True
    header_actions: bool = True
    row_actions: bool = True
    bulk_actions: bool = True
    column_sort: bool = False
    toolbar_sort: bool = False
    density: bool = False
    column_visibility: bool = False
    group_by: bool = False
    layout: bool = True


_CONTROLS: Final[dict[str, ViewControls]] = {
    "tabular": ViewControls(
        column_sort=True,
        density=True,
        column_visibility=True,
        group_by=True,
    ),
    "stacked": ViewControls(
        toolbar_sort=True,
        column_visibility=True,
    ),
    "grid": ViewControls(
        toolbar_sort=True,
    ),
    "calendar": ViewControls(),
}

_DEFAULT_CONTROLS: Final[ViewControls] = _CONTROLS["tabular"]


def normalize_data_view(view: str | None) -> DataView:
    """Return a known ``data_view``, falling back to ``tabular``."""
    if view in _CONTROLS:
        return view  # type: ignore[return-value]
    return "tabular"


def controls_for(view: str | None) -> ViewControls:
    """Return the chrome capability set for *view*."""
    return _CONTROLS.get(normalize_data_view(view), _DEFAULT_CONTROLS)


__all__ = [
    "DATA_VIEWS",
    "DATA_VIEW_OPTIONS",
    "DataView",
    "ViewControls",
    "controls_for",
    "normalize_data_view",
]
