"""Optional integration adapters for lexigram-* extension packages.

Each submodule provides a ``*Integration`` class that consumes a protocol
from ``lexigram-contracts`` and either delegates to the real extension or
provides a graceful no-op when the extension is not installed.

The module-level ``_registry`` dict is populated at boot time by
``AdminIntegrationsSubProvider.boot()`` so that consumers (e.g.
``ListRenderer``) can resolve integrations without deep constructor plumbing.
"""

from __future__ import annotations

from typing import Any

_registry: dict[str, Any] = {}


def register(name: str, instance: Any) -> None:
    """Register an integration instance for lazy access by consumers."""
    _registry[name] = instance


def get(name: str) -> Any:
    """Return a registered integration instance, or None."""
    return _registry.get(name)


__all__ = [
    "get",
    "register",
]
