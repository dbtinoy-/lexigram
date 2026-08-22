"""Revision management for the two prompt variants."""

from __future__ import annotations

from typing import Any, cast

from lexigram.ai.prompt.registry.versioned import VersionedPromptStore
from lexigram.ai.prompt.template.chat import ChatPromptTemplate

_STORE_KEY: dict[str, str] = {
    "v1": "support-v1",
    "v2": "support-v2",
}

REV2_WARMTH_NOTE = "even more warmth"


class LabVersions:
    """Variant-keyed façade over ``VersionedPromptStore``."""

    def __init__(self, max_versions: int = 10) -> None:
        self._store = VersionedPromptStore(max_versions=max_versions)

    def seed(self, factories: dict[str, Any]) -> None:
        """Push v1 rev1, v2 rev2 (warmth note in metadata) — rev1 stays."""
        self._store.push(_STORE_KEY["v1"], factories["v1"]())
        self._store.push(
            _STORE_KEY["v2"],
            factories["v2"](),
            metadata={"note": f"rev 2 baseline ({REV2_WARMTH_NOTE} pending)"},
        )
        self._store.push(
            _STORE_KEY["v2"],
            factories["v2"](),
            metadata={"note": REV2_WARMTH_NOTE},
        )

    def active(self, variant: str) -> tuple[int, ChatPromptTemplate]:
        """Current revision number and template for a variant key."""
        key = _STORE_KEY[variant]
        return self._current_rev(key), cast("ChatPromptTemplate", self._store.get(key))

    def _current_rev(self, key: str) -> int:
        for row in self._store.list_versions(key):
            if row["current"]:
                return int(row["version"])
        raise KeyError(f"no current revision for '{key}'")

    def get_revision(
        self,
        variant: str,
        rev: int,
    ) -> tuple[int, ChatPromptTemplate]:
        key = _STORE_KEY[variant]
        return rev, cast("ChatPromptTemplate", self._store.get_version(key, rev))

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
