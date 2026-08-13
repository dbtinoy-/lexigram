"""Tests for ResourceUnitRegistry (LXF-001).

RED phase — these fail because the registry doesn't exist yet.
"""

from __future__ import annotations

import pytest

pytest.importorskip("lexigram.ai.governance.resource.registry")


class TestResourceUnitRegistry:
    def test_construct_empty(self):
        from lexigram.ai.governance.resource.registry import (
            ResourceUnitRegistry,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
        )

        registry = ResourceUnitRegistry()
        assert registry.list_units() == []
        assert registry.get_unit("nonexistent") is None

    def test_register_and_lookup(self):
        from lexigram.ai.governance.resource.registry import (
            ResourceUnitRegistry,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )

        unit = ResourceUnit(
            name="render_minutes",
            unit_kind="minutes",
            window_kind=ResourceWindowKind.SLIDING,
        )
        registry = ResourceUnitRegistry()
        registry.register(unit)
        assert registry.get_unit("render_minutes") is unit
        assert registry.list_units() == [unit]

    def test_register_overwrites(self):
        from lexigram.ai.governance.resource.registry import (
            ResourceUnitRegistry,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )

        a = ResourceUnit(name="u1", unit_kind="count")
        b = ResourceUnit(name="u1", unit_kind="updated")
        registry = ResourceUnitRegistry()
        registry.register(a)
        registry.register(b)
        assert registry.get_unit("u1") is b
        assert registry.get_unit("u1").unit_kind == "updated"

    def test_from_list(self):
        from lexigram.ai.governance.resource.registry import (
            ResourceUnitRegistry,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
        )

        units = [
            ResourceUnit(name="u1", unit_kind="count"),
            ResourceUnit(name="u2", unit_kind="minutes"),
        ]
        registry = ResourceUnitRegistry.from_list(units)
        assert registry.get_unit("u1") is units[0]
        assert registry.get_unit("u2") is units[1]
        assert len(registry.list_units()) == 2

    def test_from_list_empty(self):
        from lexigram.ai.governance.resource.registry import (
            ResourceUnitRegistry,
        )

        registry = ResourceUnitRegistry.from_list([])
        assert registry.list_units() == []
