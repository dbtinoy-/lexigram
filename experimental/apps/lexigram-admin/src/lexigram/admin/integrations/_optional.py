"""Helpers for detecting and optionally integrating extension packages."""

from __future__ import annotations

import importlib.util

from lexigram.logging import get_logger

logger = get_logger(__name__)


def is_installed(module_name: str) -> bool:
    """Return True when *module_name* can be imported (not necessarily loaded)."""
    return importlib.util.find_spec(module_name) is not None


def require_or_noop(module_name: str, noop_class: type) -> object:
    """Return None if *module_name* is installed, else a *noop_class* instance.

    Callers that receive ``None`` should resolve the real implementation via
    the container.  Callers that receive a no-op instance should use it as a
    drop-in replacement.
    """
    if is_installed(module_name):
        return None
    logger.warning("optional integration %s not installed; using no-op", module_name)
    return noop_class()


__all__ = [
    "is_installed",
    "require_or_noop",
]
