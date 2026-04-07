"""ARIA attribute helper functions for accessibility utilities."""

from __future__ import annotations

from lexigram.ui.accessibility._aria_types import AriaAttrs, AriaLive, AriaRole
from lexigram.ui.core.base import el, render_to_string

# Factory functions for common ARIA patterns


def table_aria(
    label: str,
    rowcount: int | None = None,
    colcount: int | None = None,
    sortable: bool = False,
) -> dict[str, str]:
    """Return ARIA attributes for an accessible data table (grid role).

    Use on the ``<table>`` or wrapper element that contains rows and cells.
    The ``grid`` role is used instead of ``table`` to support interactive
    keyboard navigation patterns expected by Admin UI tables.

    Args:
        label: Human-readable label describing the table's content, used as
            ``aria-label``.
        rowcount: Total number of data rows across all pages.  Pass the full
            dataset size when the table is paginated so assistive technologies
            can announce ``"row N of M"``.
        colcount: Total number of columns.  Required when some columns are
            hidden or the table uses column groups.
        sortable: Reserved for future use.  Pass ``True`` to signal that
            column headers may carry ``aria-sort`` attributes.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values,
        ready to be spread onto the element.

    Example::

        attrs = table_aria("User list", rowcount=250, colcount=5)
        # {"role": "grid", "aria-label": "User list",
        #  "aria-rowcount": "250", "aria-colcount": "5"}
    """
    attrs = AriaAttrs(
        role=AriaRole.GRID,
        label=label,
        rowcount=rowcount,
        colcount=colcount,
    )
    return attrs.to_dict()


def row_aria(
    index: int,
    selected: bool = False,
    expanded: bool | None = None,
) -> dict[str, str]:
    """Return ARIA attributes for a table row element.

    Args:
        index: 1-based row position within the full dataset (not the current
            page).  Maps to ``aria-rowindex``.
        selected: Whether this row is currently selected.  Maps to
            ``aria-selected``.
        expanded: For tree-grid rows, whether the row is expanded.  Pass
            ``None`` (default) to omit the attribute entirely.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.
    """
    attrs = AriaAttrs(
        role=AriaRole.ROW,
        rowindex=index,
        selected=selected,
        expanded=expanded,
    )
    return attrs.to_dict()


def cell_aria(
    colindex: int | None = None,
    rowindex: int | None = None,
) -> dict[str, str]:
    """Return ARIA attributes for an interactive table data cell.

    Uses the ``gridcell`` role, which is appropriate for cells inside a
    ``grid``-role container that supports keyboard interaction.

    Args:
        colindex: 1-based column position within the full column set.  Maps
            to ``aria-colindex``.  Required when columns are hidden.
        rowindex: 1-based row position within the full dataset.  Maps to
            ``aria-rowindex``.  Usually set on the row element instead;
            provide here only when the row element cannot be annotated.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.
    """
    attrs = AriaAttrs(
        role=AriaRole.GRIDCELL,
        colindex=colindex,
        rowindex=rowindex,
    )
    return attrs.to_dict()


def header_aria(
    label: str,
    sortable: bool = False,
    sort_direction: str | None = None,
) -> dict[str, str]:
    """Return ARIA attributes for a sortable or static column header cell.

    Args:
        label: Accessible name for the column, mapped to ``aria-label``.
        sortable: When ``True``, adds an ``aria-sort`` attribute to indicate
            the column participates in sorting.  Defaults to ``False``.
        sort_direction: Current sort direction.  Pass ``"asc"`` for ascending,
            ``"desc"`` for descending, or ``None`` (default) to output
            ``aria-sort="none"`` when *sortable* is ``True``.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.

    Example::

        attrs = header_aria("Name", sortable=True, sort_direction="asc")
        # {"role": "columnheader", "aria-label": "Name", "aria-sort": "ascending"}
    """
    sort = None
    if sortable:
        if sort_direction == "asc":
            sort = "ascending"
        elif sort_direction == "desc":
            sort = "descending"
        else:
            sort = "none"

    attrs = AriaAttrs(
        role=AriaRole.COLUMNHEADER,
        label=label,
        sort=sort,
    )
    return attrs.to_dict()


def button_aria(
    label: str,
    pressed: bool | None = None,
    expanded: bool | None = None,
    controls: str | None = None,
    haspopup: str | None = None,
    disabled: bool = False,
) -> dict[str, str]:
    """Return ARIA attributes for an interactive button element.

    Covers toggle buttons, disclosure buttons, and menu-trigger buttons.  Pass
    only the arguments relevant to the button's role; unused attributes are
    omitted from the returned dict.

    Args:
        label: Accessible name for the button, mapped to ``aria-label``.
        pressed: For toggle buttons, the current pressed state.  ``True``
            maps to ``aria-pressed="true"``, ``False`` to ``"false"``, ``None``
            omits the attribute entirely.
        expanded: For disclosure/accordion buttons, whether the controlled
            region is currently visible.  Maps to ``aria-expanded``.
        controls: ID of the element this button controls.  Maps to
            ``aria-controls``.
        haspopup: Type of popup this button opens, e.g. ``"menu"``,
            ``"listbox"``, ``"dialog"``.  Maps to ``aria-haspopup``.
        disabled: When ``True``, adds ``aria-disabled="true"``.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.

    Example::

        attrs = button_aria("Toggle sidebar", expanded=False, controls="sidebar")
        # {"role": "button", "aria-label": "Toggle sidebar",
        #  "aria-expanded": "false", "aria-controls": "sidebar"}
    """
    attrs = AriaAttrs(
        role=AriaRole.BUTTON,
        label=label,
        pressed=pressed,
        expanded=expanded,
        controls=controls,
        haspopup=haspopup,
        disabled=disabled if disabled else None,
    )
    return attrs.to_dict()


def dialog_aria(
    label: str,
    describedby: str | None = None,
    modal: bool = True,
) -> dict[str, str]:
    """Return ARIA attributes for a modal or non-modal dialog overlay.

    Args:
        label: Accessible name for the dialog, mapped to ``aria-label``.  Use
            a concise title that describes the dialog's purpose, e.g.
            ``"Confirm deletion"``.
        describedby: ID of an element that provides a longer description of
            the dialog's purpose.  Maps to ``aria-describedby``.
        modal: When ``True`` (default), adds ``aria-modal="true"`` to signal
            that background content is inert while the dialog is open.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.

    Example::

        attrs = dialog_aria("Delete user", describedby="delete-desc")
        # {"role": "dialog", "aria-label": "Delete user",
        #  "aria-describedby": "delete-desc", "aria-modal": "true"}
    """
    attrs = AriaAttrs(
        role=AriaRole.DIALOG,
        label=label,
        describedby=describedby,
    )
    result = attrs.to_dict()
    if modal:
        result["aria-modal"] = "true"
    return result


def search_aria(
    label: str = "Search",
    controls: str | None = None,
) -> dict[str, str]:
    """Return ARIA attributes for a search input field.

    Args:
        label: Accessible name for the search field.  Defaults to
            ``"Search"``.
        controls: ID of the live region or results container that this input
            updates.  Maps to ``aria-controls`` and helps screen readers
            announce that results are available.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.
    """
    attrs = AriaAttrs(
        role=AriaRole.SEARCHBOX,
        label=label,
        controls=controls,
    )
    return attrs.to_dict()


def live_region_aria(
    politeness: AriaLive = AriaLive.POLITE,
    atomic: bool = True,
) -> dict[str, str]:
    """Return ARIA attributes for a live region container.

    Live regions allow assistive technologies to announce dynamic content
    changes without requiring user focus.  Use :func:`announce` for
    one-shot screen-reader announcements; use this function when you need
    to annotate a persistent container.

    Args:
        politeness: Interrupt behaviour for the announcement.  Use
            :attr:`AriaLive.POLITE` (default) to wait until the user is
            idle, or :attr:`AriaLive.ASSERTIVE` for time-sensitive alerts.
        atomic: When ``True`` (default), the entire region is re-read on
            every change rather than just the changed nodes.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.
    """
    attrs = AriaAttrs(
        live=politeness,
        atomic=atomic,
    )
    return attrs.to_dict()


def tab_aria(
    label: str,
    selected: bool = False,
    controls: str | None = None,
) -> dict[str, str]:
    """Return ARIA attributes for a tab button within a tab list.

    The tab element must be a child of an element with ``role="tablist"``
    and must reference its associated panel via *controls*.

    Args:
        label: Accessible name for the tab, mapped to ``aria-label``.
        selected: Whether this tab is currently the active tab.  Maps to
            ``aria-selected``.
        controls: ID of the ``tabpanel`` element this tab reveals.  Maps
            to ``aria-controls``.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.
    """
    attrs = AriaAttrs(
        role=AriaRole.TAB,
        label=label,
        selected=selected,
        controls=controls,
    )
    return attrs.to_dict()


def tabpanel_aria(
    labelledby: str,
    hidden: bool = False,
) -> dict[str, str]:
    """Return ARIA attributes for a tab panel content area.

    The panel must be associated with its controlling tab via *labelledby*.

    Args:
        labelledby: ID of the ``tab`` element that controls this panel.  Maps
            to ``aria-labelledby``.
        hidden: When ``True``, adds ``aria-hidden="true"`` to hide the panel
            from assistive technologies when its tab is not selected.

    Returns:
        A ``dict[str, str]`` of HTML attribute names to their string values.
    """
    attrs = AriaAttrs(
        role=AriaRole.TABPANEL,
        labelledby=labelledby,
        hidden=hidden if hidden else None,
    )
    return attrs.to_dict()


# Screen reader announcements


def announce(
    message: str,
    priority: AriaLive = AriaLive.POLITE,
    atomic: bool = True,
) -> str:
    """
    Create an invisible live region announcement.

    This element will be announced by screen readers when inserted
    into the DOM. Use for dynamic content updates.

    Args:
        message: The text to announce
        priority: POLITE (wait for idle) or ASSERTIVE (immediate)
        atomic: Whether to announce the entire region or just changes

    Returns:
        HTML string for the announcement element
    """
    return render_to_string(
        el(
            "div",
            message,
            class_="sr-only",
            role="status",
            **live_region_aria(priority, atomic),
        ),
    )


def announce_table_update(
    total: int,
    page: int | None = None,
    search: str | None = None,
) -> str:
    """Create a polite screen-reader announcement for a table data refresh.

    Composes a human-readable summary of the current table state and emits
    it as a ``POLITE`` live-region element via :func:`announce`.

    Args:
        total: Total number of items currently displayed or matching the
            current filter.
        page: Current page number when the table is paginated.  Omit (or
            pass ``None``) for unpaginated tables.
        search: Active search / filter text.  When provided, the message
            includes ``"filtered by '<term>'"``.

    Returns:
        An HTML string containing the invisible announcement element.
    """
    parts = [f"{total} items"]
    if page:
        parts.append(f"page {page}")
    if search:
        parts.append(f"filtered by '{search}'")

    message = ", ".join(parts)
    return announce(message)


def announce_selection_change(
    count: int,
    action: str = "selected",
) -> str:
    """Create a polite screen-reader announcement for a selection state change.

    Args:
        count: Number of items currently in the selection.
        action: Past-tense verb describing the selection action, e.g.
            ``"selected"`` (default) or ``"deselected"``.

    Returns:
        An HTML string containing the invisible announcement element.
    """
    if count == 0:
        message = "No items selected"
    elif count == 1:
        message = f"1 item {action}"
    else:
        message = f"{count} items {action}"

    return announce(message)


def announce_action_complete(
    action: str,
    success: bool = True,
) -> str:
    """Create an assertive screen-reader announcement for an action outcome.

    Uses ``ASSERTIVE`` politeness so the result is announced immediately,
    interrupting any in-progress speech.  Suitable for confirming or
    reporting the failure of a user-initiated action.

    Args:
        action: Human-readable description of the action, e.g.
            ``"User deleted"`` or ``"Export"``.
        success: When ``True`` (default), appends ``"completed successfully"``;
            when ``False``, appends ``"failed"``.

    Returns:
        An HTML string containing the invisible announcement element.
    """
    status = "completed successfully" if success else "failed"
    return announce(f"{action} {status}", priority=AriaLive.ASSERTIVE)


def SkipLink(
    target_id: str = "main-content", label: str = "Skip to main content"
) -> str:
    """Return an HTML skip navigation link for accessibility.

    Args:
        target_id: The ID of the target element to skip to.
        label: The link text for the skip link.

    Returns:
        An HTML anchor tag with sr-only CSS class.
    """
    return f'<a href="#{target_id}" class="sr-only">{label}</a>'


def keyboard_navigation_script() -> str:
    """Return a script tag with keyboard navigation helpers.

    Returns:
        An HTML script tag with keyboard navigation JavaScript.
    """
    return '<script>document.addEventListener("keydown",function(e){if(e.key==="ArrowDown"){e.preventDefault();}if(e.key==="ArrowUp"){e.preventDefault();}if(e.key==="Escape"){e.preventDefault();}if(e.key==="/"){document.body.classList.add("keyboard-nav");}});</script>'


__all__ = [
    "SkipLink",
    "announce",
    "announce_action_complete",
    "announce_selection_change",
    "announce_table_update",
    "button_aria",
    "cell_aria",
    "dialog_aria",
    "header_aria",
    "keyboard_navigation_script",
    "live_region_aria",
    "row_aria",
    "search_aria",
    "tab_aria",
    "table_aria",
    "tabpanel_aria",
]
