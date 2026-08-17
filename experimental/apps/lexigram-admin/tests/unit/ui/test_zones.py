"""
Unit tests for the Zone-based UI architecture.

Tests the zones.py module which provides:
- Zone dataclass for defining UI regions
- Zones registry for all targetable zones
- SwapMode enum for HTMX swap modes
"""

import pytest

from lexigram.ui.core.zones import SwapMode, Zone, Zones


class TestSwapMode:
    """Tests for SwapMode enum."""

    def test_swap_mode_values(self):
        """SwapMode values should match HTMX swap modes."""
        assert SwapMode.OUTER_HTML.value == "outerHTML"
        assert SwapMode.INNER_HTML.value == "innerHTML"
        assert SwapMode.BEFORE_END.value == "beforeend"
        assert SwapMode.AFTER_BEGIN.value == "afterbegin"
        assert SwapMode.NONE.value == "none"


class TestZone:
    """Tests for Zone dataclass."""

    def test_zone_creation(self):
        """Zone should be created with required fields."""
        zone = Zone(
            id="test-zone",
            description="A test zone",
            swappable=True,
            swap_mode=SwapMode.INNER_HTML,
        )
        assert zone.id == "test-zone"
        assert zone.description == "A test zone"
        assert zone.swappable is True
        assert zone.swap_mode == SwapMode.INNER_HTML

    def test_zone_selector_property(self):
        """Zone.selector should return CSS ID selector."""
        zone = Zone(
            id="my-zone",
            description="Test",
            swappable=True,
            swap_mode=SwapMode.INNER_HTML,
        )
        assert zone.selector == "#my-zone"

    def test_zone_str_returns_id(self):
        """str(zone) should return the zone ID."""
        zone = Zone(
            id="my-zone",
            description="Test",
            swappable=True,
            swap_mode=SwapMode.INNER_HTML,
        )
        assert str(zone) == "my-zone"

    def test_zone_repr(self):
        """repr(zone) should be informative."""
        zone = Zone(
            id="my-zone",
            description="Test",
            swappable=True,
            swap_mode=SwapMode.INNER_HTML,
        )
        assert repr(zone) == "Zone('my-zone')"

    def test_zone_is_frozen(self):
        """Zone should be immutable (frozen dataclass)."""
        zone = Zone(
            id="my-zone",
            description="Test",
            swappable=True,
            swap_mode=SwapMode.INNER_HTML,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            zone.id = "changed"

    def test_zone_default_values(self):
        """Zone should have sensible defaults."""
        zone = Zone(
            id="test",
            description="Test",
            swappable=True,
            swap_mode=SwapMode.INNER_HTML,
        )
        assert zone.preserve_alpine is False
        assert zone.oob_only is False


class TestZones:
    """Tests for Zones registry."""

    def test_zones_all_returns_list(self):
        """Zones.all_zones() should return a list of all zones."""
        all_zones = Zones.all_zones()
        assert isinstance(all_zones, list)
        assert len(all_zones) > 0
        assert all(isinstance(z, Zone) for z in all_zones)

    def test_zones_unique_ids(self):
        """All zones should have unique IDs."""
        ids = list(map(lambda z: z.id, Zones.all_zones()))
        assert len(ids) == len(set(ids)), "Duplicate zone IDs found"

    def test_zones_valid_selectors(self):
        """All zone selectors should be valid CSS ID selectors."""
        for zone in Zones.all_zones():
            assert zone.selector.startswith("#"), f"{zone.id} selector missing #"
            assert " " not in zone.selector, f"{zone.id} selector has spaces"

    def test_zones_table_exists(self):
        """TABLE zone should exist and be the root scope."""
        assert Zones.TABLE is not None
        assert Zones.TABLE.id == "lexigram-table"
        assert Zones.TABLE.swappable is True
        assert Zones.TABLE.swap_mode == SwapMode.OUTER_HTML

    def test_zones_data_exists(self):
        """DATA zone should exist for content updates."""
        assert Zones.DATA is not None
        assert Zones.DATA.id == "table-data"
        assert Zones.DATA.swappable is True
        assert Zones.DATA.swap_mode == SwapMode.INNER_HTML
        assert Zones.DATA.preserve_alpine is True

    def test_zones_toolbar_is_oob_only(self):
        """TOOLBAR zone should be OOB-only."""
        assert Zones.TOOLBAR.oob_only is True

    def test_zones_filters_is_oob_only(self):
        """FILTERS zone should be OOB-only."""
        assert Zones.FILTERS.oob_only is True

    def test_zones_search_not_swappable(self):
        """SEARCH zone should not be swappable (preserve focus)."""
        assert Zones.SEARCH.swappable is False
        assert Zones.SEARCH.swap_mode == SwapMode.NONE

    def test_zones_modal_exists(self):
        """MODAL zone should exist for dialogs."""
        assert Zones.MODAL is not None
        assert Zones.MODAL.swappable is True

    def test_zones_slide_over_exists(self):
        """SLIDE_OVER zone should exist for forms."""
        assert Zones.SLIDE_OVER is not None
        assert Zones.SLIDE_OVER.swappable is True

    def test_zones_flash_exists(self):
        """FLASH zone should exist for notifications."""
        assert Zones.FLASH is not None
        assert Zones.FLASH.swappable is True

    def test_zones_get_by_id(self):
        """Zones.get_by_id() should find zones by ID."""
        zone = Zones.get_by_id("lexigram-table")
        assert zone == Zones.TABLE

        zone = Zones.get_by_id("table-data")
        assert zone == Zones.DATA

    def test_zones_get_by_id_not_found(self):
        """Zones.get_by_id() should return None for unknown IDs."""
        zone = Zones.get_by_id("nonexistent-zone")
        assert zone is None

    def test_zones_get_by_selector(self):
        """Zones.get_by_selector() should find zones by CSS selector."""
        zone = Zones.get_by_selector("#lexigram-table")
        assert zone == Zones.TABLE

        # Should also work without #
        zone = Zones.get_by_selector("table-data")
        assert zone == Zones.DATA

    def test_zones_swappable_returns_only_swappable(self):
        """Zones.swappable() should return only swappable zones."""
        swappable = Zones.swappable()
        assert all(z.swappable for z in swappable)
        assert Zones.TABLE in swappable
        assert Zones.DATA in swappable
        assert Zones.SEARCH not in swappable  # Not swappable
