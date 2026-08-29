"""Optional integration adapters for lexigram-* extension packages.

Each submodule provides a ``*Integration`` class that consumes a protocol
from ``lexigram-contracts`` and either delegates to the real extension or
provides a graceful no-op when the extension is not installed.

The registry is populated at boot time by
``AdminIntegrationsSubProvider.boot()`` so that consumers (e.g.
``ListRenderer``) can resolve integrations without deep constructor plumbing.
"""

from __future__ import annotations

from typing import Any

from lexigram.primitives.registry import Registry


class IntegrationRegistry(Registry[str, Any]):
    """Registry of live integration adapters, keyed by class name.

    Plugin-style registry (no built-in set): instances are registered
    explicitly by ``AdminIntegrationsSubProvider.boot()``.  Consumers use
    :func:`get` on the module-level instance.
    """

    def __init__(self) -> None:
        """Create an empty integration registry."""
        super().__init__(
            name="admin.integrations",
            allow_overwrite=True,
        )


#: Module-level registry instance (populated at boot time).
_registry = IntegrationRegistry()


def register(name: str, instance: object) -> None:
    """Register an integration instance for lazy access by consumers."""
    _registry.register(name, instance)


def get(name: str) -> Any | None:
    """Return a registered integration instance, or None."""
    return _registry.get(name)


__all__ = [
    "IntegrationRegistry",
    "get",
    "register",
]
