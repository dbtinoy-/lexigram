"""Lightweight in-memory provider designed for use in tests.

Unlike :class:`~lexigram.feature_flags.backends.local.LocalProvider` this
provider works with plain booleans and supports per-flag *overrides* that
short-circuit normal evaluation — making it easy to force specific outcomes
in unit tests without wiring a full flag configuration.
"""

from __future__ import annotations

from typing import Any

from lexigram.features.backends.local import LocalProvider
from lexigram.features.types import Flag, FlagContext, FlagEvaluation, FlagType


class MemoryProvider(LocalProvider):
    """Lightweight in-memory provider designed for use in tests.

    Unlike :class:`~lexigram.feature_flags.backends.local.LocalProvider` this
    provider works with plain booleans and supports per-flag *overrides* that
    short-circuit normal evaluation.

    .. note::
        **Choosing between in-memory providers:**

        * Use :class:`MemoryProvider` (this class) in **unit tests** — the
          ``_overrides`` dict lets you force specific flag outcomes without
          touching the flag configuration.

        * Use :class:`~lexigram.features.backends.local.LocalProvider`
          for production single-node deployments or integration tests where
          you only need ``set_flag`` / ``get_flag`` semantics and do not need
          per-test overrides.

    Typical usage in tests::

        provider = MemoryProvider()
        provider.set_flag("new_billing", enabled=True)
        manager = FlagManager(provider)
    """

    def __init__(self) -> None:
        super().__init__()
        self._overrides: dict[str, FlagEvaluation] = {}

    # -- Evaluation (checks overrides first) --------------------------------

    async def evaluate(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Evaluate, applying any explicit test override first."""
        if name in self._overrides:
            return self._overrides[name]
        return await super().evaluate(name, context)

    def evaluate_sync(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Synchronous evaluation, applying overrides first."""
        if name in self._overrides:
            return self._overrides[name]
        return super().evaluate_sync(name, context)

    # -- Test helpers -------------------------------------------------------

    def set_flag_sync(self, name: str, value: bool) -> None:
        """Define a simple boolean flag (sync version)."""
        self._flags[name] = Flag(name=name, type=FlagType.BOOLEAN, enabled=value)

    async def set_flag(self, name: str, value: bool) -> None:
        """Define a simple boolean flag."""
        self.set_flag_sync(name, value)

    def override(
        self,
        name: str,
        *,
        enabled: bool,
        value: Any = None,
        reason: str = "test_override",
    ) -> None:
        """Register a hard override for *name* that bypasses normal evaluation."""
        self._overrides[name] = FlagEvaluation(
            flag_name=name,
            enabled=enabled,
            reason=reason,
            value=value if value is not None else enabled,
        )

    def clear_override(self, name: str) -> None:
        """Remove the test override for *name*."""
        self._overrides.pop(name, None)

    def reset(self) -> None:
        """Clear all flags and overrides."""
        self._flags.clear()
        self._overrides.clear()


__all__ = ["MemoryProvider"]
