"""ARIA type definitions and dataclasses for accessibility utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AriaLive(str, Enum):
    """ARIA live region politeness settings."""

    OFF = "off"
    POLITE = "polite"  # Announced when user is idle
    ASSERTIVE = "assertive"  # Announced immediately


class AriaRole(str, Enum):
    """Common ARIA roles for components."""

    # Landmark roles
    BANNER = "banner"
    NAVIGATION = "navigation"
    MAIN = "main"
    COMPLEMENTARY = "complementary"
    CONTENTINFO = "contentinfo"
    SEARCH = "search"
    REGION = "region"

    # Widget roles
    BUTTON = "button"
    CHECKBOX = "checkbox"
    DIALOG = "dialog"
    ALERTDIALOG = "alertdialog"
    GRID = "grid"
    GRIDCELL = "gridcell"
    LISTBOX = "listbox"
    MENU = "menu"
    MENUITEM = "menuitem"
    OPTION = "option"
    PROGRESSBAR = "progressbar"
    RADIO = "radio"
    RADIOGROUP = "radiogroup"
    ROW = "row"
    ROWGROUP = "rowgroup"
    ROWHEADER = "rowheader"
    COLUMNHEADER = "columnheader"
    SEARCHBOX = "searchbox"
    SLIDER = "slider"
    SPINBUTTON = "spinbutton"
    SWITCH = "switch"
    TAB = "tab"
    TABLIST = "tablist"
    TABPANEL = "tabpanel"
    TEXTBOX = "textbox"
    TOOLBAR = "toolbar"
    TOOLTIP = "tooltip"
    TREE = "tree"
    TREEITEM = "treeitem"

    # Live region roles
    ALERT = "alert"
    LOG = "log"
    MARQUEE = "marquee"
    STATUS = "status"
    TIMER = "timer"


@dataclass
class AriaAttrs:
    """Builder for ARIA attributes."""

    role: AriaRole | None = None
    label: str | None = None
    labelledby: str | None = None
    describedby: str | None = None
    live: AriaLive | None = None
    atomic: bool | None = None
    busy: bool | None = None
    controls: str | None = None
    expanded: bool | None = None
    haspopup: str | None = None
    hidden: bool | None = None
    invalid: bool | None = None
    pressed: bool | None = None
    selected: bool | None = None
    disabled: bool | None = None
    current: str | None = None
    sort: str | None = None
    rowcount: int | None = None
    colcount: int | None = None
    rowindex: int | None = None
    colindex: int | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to HTML attribute dictionary."""
        attrs = {}

        if self.role:
            attrs["role"] = self.role.value
        if self.label:
            attrs["aria-label"] = self.label
        if self.labelledby:
            attrs["aria-labelledby"] = self.labelledby
        if self.describedby:
            attrs["aria-describedby"] = self.describedby
        if self.live:
            attrs["aria-live"] = self.live.value
        if self.atomic is not None:
            attrs["aria-atomic"] = "true" if self.atomic else "false"
        if self.busy is not None:
            attrs["aria-busy"] = "true" if self.busy else "false"
        if self.controls:
            attrs["aria-controls"] = self.controls
        if self.expanded is not None:
            attrs["aria-expanded"] = "true" if self.expanded else "false"
        if self.haspopup:
            attrs["aria-haspopup"] = self.haspopup
        if self.hidden is not None:
            attrs["aria-hidden"] = "true" if self.hidden else "false"
        if self.invalid is not None:
            attrs["aria-invalid"] = "true" if self.invalid else "false"
        if self.pressed is not None:
            attrs["aria-pressed"] = "true" if self.pressed else "false"
        if self.selected is not None:
            attrs["aria-selected"] = "true" if self.selected else "false"
        if self.disabled is not None:
            attrs["aria-disabled"] = "true" if self.disabled else "false"
        if self.current:
            attrs["aria-current"] = self.current
        if self.sort:
            attrs["aria-sort"] = self.sort
        if self.rowcount is not None:
            attrs["aria-rowcount"] = str(self.rowcount)
        if self.colcount is not None:
            attrs["aria-colcount"] = str(self.colcount)
        if self.rowindex is not None:
            attrs["aria-rowindex"] = str(self.rowindex)
        if self.colindex is not None:
            attrs["aria-colindex"] = str(self.colindex)

        return attrs


__all__ = [
    "AriaAttrs",
    "AriaLive",
    "AriaRole",
]
