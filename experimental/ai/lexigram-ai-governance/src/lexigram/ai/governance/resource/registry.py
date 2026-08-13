"""Resource unit registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai.governance.resource_unit import ResourceUnit


class ResourceUnitRegistry:
    """In-memory registry of known ResourceUnit definitions.

    Populated at boot from ``GovernanceConfig.resource_units`` via the DI
    provider.  Lookup is by unit name (``ResourceUnit.name``).
    """

    def __init__(self) -> None:
        self._units: dict[str, ResourceUnit] = {}

    def register(self, unit: ResourceUnit) -> None:
        """Register (or overwrite) a resource unit definition."""
        self._units[unit.name] = unit

    def get_unit(self, name: str) -> ResourceUnit | None:
        """Look up a resource unit by name, or ``None``."""
        return self._units.get(name)

    def list_units(self) -> list[ResourceUnit]:
        """Return all registered resource units."""
        return list(self._units.values())

    @classmethod
    def from_list(cls, units: list[ResourceUnit]) -> ResourceUnitRegistry:
        """Create a registry pre-populated with *units*."""
        registry = cls()
        for u in units:
            registry.register(u)
        return registry


__all__ = ["ResourceUnitRegistry"]
