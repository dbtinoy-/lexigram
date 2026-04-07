"""
Zone-Based UI Architecture for Lexigram Admin.

A Zone is a DOM subtree with:
- A unique ID
- A defined responsibility
- Clear rules about what can swap it
- A contract for what it contains

This module provides the central registry of all UI zones, replacing
the scattered IDs in consts.py with a structured, type-safe system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class SwapMode(str, Enum):
    """Valid HTMX swap modes."""

    OUTER_HTML = "outerHTML"
    INNER_HTML = "innerHTML"
    BEFORE_END = "beforeend"
    AFTER_BEGIN = "afterbegin"
    NONE = "none"


@dataclass(frozen=True)
class Zone:
    """
    Definition of a UI zone.

    A zone represents a targetable region of the page with specific
    semantics for how it can be updated via HTMX.

    Attributes:
        id: The HTML element ID for this zone
        description: Human-readable description of this zone's purpose
        swappable: Whether this zone can be targeted by HTMX swaps
        swap_mode: The default HTMX swap mode for this zone
        preserve_alpine: Whether Alpine.js state should be preserved on swap
        oob_only: If True, this zone should only be updated via OOB swaps
    """

    id: str
    description: str
    swappable: bool
    swap_mode: SwapMode
    preserve_alpine: bool = False
    oob_only: bool = False

    @property
    def selector(self) -> str:
        """Return the CSS selector for this zone."""
        return f"#{self.id}"

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Zone({self.id!r})"


class Zones:
    """
    Central registry of all UI zones.

    This class provides a single source of truth for all targetable
    regions in the admin UI. Components should reference these zones
    rather than hardcoding IDs.

    Zone Hierarchy:

        TABLE (root scope)
        ├── TOOLBAR (switchers, header actions) - OOB only
        ├── SEARCH (search input) - never swap
        ├── FILTERS (filter bar) - OOB only
        └── DATA (rows + pagination) - most common target

        DASHBOARD (dashboard page)
        └── WIDGET_CONTAINER (per-widget lazy-load target)

        MODAL (global, outside table)
        SLIDE_OVER (global, outside table)
        FLASH (toast notifications)

    Usage:
        from lexigram.ui.core.zones import Zones

        attrs = {
            "hx-target": Zones.DATA.selector,
            "hx-swap": Zones.DATA.swap_mode.value,
        }
    """

    # === Primary Zones ===

    TABLE: ClassVar[Zone] = Zone(
        id="lexigram-table",
        description="Root table scope with Alpine.js state. Target for full refresh only.",
        swappable=True,
        swap_mode=SwapMode.OUTER_HTML,
        preserve_alpine=False,  # Full refresh reinitializes Alpine
    )

    DATA: ClassVar[Zone] = Zone(
        id="table-data",
        description="Data content + pagination. Most common target for data updates.",
        swappable=True,
        swap_mode=SwapMode.INNER_HTML,
        preserve_alpine=True,  # Parent Alpine scope preserved
    )

    # === Secondary Zones (typically OOB) ===

    TOOLBAR: ClassVar[Zone] = Zone(
        id="table-toolbar",
        description="Switchers and header actions. Update via OOB only.",
        swappable=True,
        swap_mode=SwapMode.OUTER_HTML,
        oob_only=True,
    )

    FILTERS: ClassVar[Zone] = Zone(
        id="table-filters",
        description="Filter controls. Update via OOB when filter options change.",
        swappable=True,
        swap_mode=SwapMode.OUTER_HTML,
        oob_only=True,
    )

    # === Non-Swappable Zones ===

    SEARCH: ClassVar[Zone] = Zone(
        id="table-search",
        description="Search input. Never swap to preserve focus and input state.",
        swappable=False,
        swap_mode=SwapMode.NONE,
    )

    # === Global Zones (outside table scope) ===

    MODAL: ClassVar[Zone] = Zone(
        id="modal-container",
        description="Modal dialogs. Target for modal actions.",
        swappable=True,
        swap_mode=SwapMode.INNER_HTML,
    )

    SLIDE_OVER: ClassVar[Zone] = Zone(
        id="slide-over-container",
        description="Side panel forms. Target for edit/create actions.",
        swappable=True,
        swap_mode=SwapMode.INNER_HTML,
    )

    FLASH: ClassVar[Zone] = Zone(
        id="flash-container",
        description="Toast/flash notifications.",
        swappable=True,
        swap_mode=SwapMode.INNER_HTML,
    )

    # === Dashboard Zones ===

    DASHBOARD_GRID: ClassVar[Zone] = Zone(
        id="dashboard-grid",
        description="Main dashboard widget grid container. Swappable for full dashboard refresh.",
        swappable=True,
        swap_mode=SwapMode.INNER_HTML,
    )

    WIDGET_CONTAINER: ClassVar[Zone] = Zone(
        id="widget-container",
        description="Individual widget card. Used for per-widget HTMX lazy-load and refresh.",
        swappable=True,
        swap_mode=SwapMode.INNER_HTML,
        preserve_alpine=True,
    )

    # === Bulk Action Zone ===

    BULK_BAR: ClassVar[Zone] = Zone(
        id="table-bulk-bar",
        description="Bulk action buttons shown when items selected. Controlled by Alpine.",
        swappable=False,  # Visibility controlled by Alpine x-show
        swap_mode=SwapMode.NONE,
    )

    @classmethod
    def all_zones(cls) -> list[Zone]:
        """Return all registered zones."""
        return [
            cls.TABLE,
            cls.DATA,
            cls.TOOLBAR,
            cls.FILTERS,
            cls.SEARCH,
            cls.MODAL,
            cls.SLIDE_OVER,
            cls.FLASH,
            cls.DASHBOARD_GRID,
            cls.WIDGET_CONTAINER,
            cls.BULK_BAR,
        ]

    @classmethod
    def swappable(cls) -> list[Zone]:
        """Return all zones that can be targeted by HTMX swaps."""
        return list(filter(lambda z: z.swappable, cls.all_zones()))

    @classmethod
    def get_by_id(cls, zone_id: str) -> Zone | None:
        """
        Look up a zone by its ID.

        Returns None if no zone with that ID exists.
        """
        for zone in cls.all_zones():
            if zone.id == zone_id:
                return zone
        return None

    @classmethod
    def get_by_selector(cls, selector: str) -> Zone | None:
        """
        Look up a zone by its CSS selector.

        Handles both "#zone-id" and "zone-id" formats.
        """
        # Normalize selector
        zone_id = selector[1:] if selector.startswith("#") else selector
        return cls.get_by_id(zone_id)
