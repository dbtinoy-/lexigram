"""Unified Registry foundation for Lexigram Framework.

Re-exports from submodules so that ``from lexigram.primitives.registry import X``
continues to work unchanged.
"""

from __future__ import annotations

from lexigram.primitives.registry.core import (
    BackendRegistry,
    Registry,
    StrategyRegistry,
    on_register,
    on_unregister,
)
from lexigram.primitives.registry.introspection import (
    RegistryIntrospector,
    entry_point_catalog,
    registry_info,
)

__all__ = [
    "BackendRegistry",
    "Registry",
    "RegistryIntrospector",
    "StrategyRegistry",
    "entry_point_catalog",
    "on_register",
    "on_unregister",
    "registry_info",
]
