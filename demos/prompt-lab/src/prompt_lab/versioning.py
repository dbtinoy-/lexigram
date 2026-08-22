"""Revision management for the two prompt variants."""

from __future__ import annotations

from typing import Any

from lexigram.ai.prompt.registry.versioned import VersionedPromptStore
from lexigram.ai.prompt.template.base import AbstractPromptTemplate

_STORE_KEY: dict[str, str] = {
    "v1": "support-v1",
    "v2": "support-v2",
}

_V2_WARMTH_NOTE = (
    "Add one extra sentence of empathy before helping. "
    "(rev 3: even more warmth)"
)


class LabVersions:
    """Variant-keyed façade over ``VersionedPromptStore``."""

    def __init__(self, max_versions: int = 10) -> None:
        self._store = VersionedPromptStore(max_versions=max_versions)

    def seed(self, factories: dict[str, Any]) -> None:
        """Push v1 rev1, v2 rev2 (empathy tweak) — v2 rev1 stays as base."""
        self._store.push(_STORE_KEY["v1"], factories["v1"]())
        self._store.push(_STORE_KEY["v2"], factories["v2"]())
        warmed = factories["v2"]()
        warmed._system = f"{warmed._system}\n{_V2_WARMTH_NOTE}"
        self._store.push(_STORE_KEY["v2"], warmed)

    def active(self, variant: str) -> tuple[int, AbstractPromptTemplate]:
        """Current revision number and template for a variant key."""
        key = _STORE_KEY[variant]
        return self._current_rev(key), self._store.get(key)

    def _current_rev(self, key: str) -> int:
        for row in self._store.list_versions(key):
            if row["current"]:
                return int(row["version"])
        raise KeyError(f"no current revision for '{key}'")

    def get_revision(
        self, variant: str, rev: int,
    ) -> tuple[int, AbstractPromptTemplate]:
        key = _STORE_KEY[variant]
        return rev, self._store.get_version(key, rev)

    def rollback(self, variant: str, steps: int = 1) -> int:
        """Step the pointer back; return the new active revision."""
        key = _STORE_KEY[variant]
        self._store.rollback(key, steps=steps)
        return self._current_rev(key)

    def history(self, variant: str) -> list[dict[str, Any]]:
        key = _STORE_KEY[variant]
        return [
            {
                "rev": int(row["version"]),
                "current": bool(row["current"]),
                "metadata": dict(row["metadata"]),
            }
            for row in self._store.list_versions(key)
        ]
