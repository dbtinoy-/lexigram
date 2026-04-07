from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)


class NameCollisionError(Exception):
    """Raised when a name collision occurs in error mode."""


class NamingPolicy:
    """Namespacing and collision detection for contributor surface names."""

    def __init__(self, mode: Literal["warn", "error"] = "warn") -> None:
        self._mode = mode
        self._seen: dict[str, dict[str, str]] = {}

    def namespaced(self, package_source: str, name: str) -> str:
        """Prefix *name* with *package_source* unless already prefixed."""
        prefix = f"{package_source}."
        if name.startswith(prefix):
            return name
        return f"{prefix}{name}"

    def register(self, kind: str, name: str) -> None:
        """Record a name under *kind*; warn or raise on collision."""
        if name in self._seen.setdefault(kind, {}):
            if self._mode == "error":
                raise NameCollisionError(
                    f"collision on {kind} '{name}': "
                    f"already registered by "
                    f"'{self._seen[kind][name]}'"
                )
            logger.warning(
                "collision on %s '%s'",
                kind,
                name,
                extra={"item_kind": kind, "item_name": name},
            )
        else:
            self._seen[kind][name] = name
