"""In-memory, code-defined flag provider.

Suitable for flags defined at application startup (e.g. loaded from a
config file), single-node applications, and as a base layer in a
:class:`~lexigram.feature_flags.backends.chained.ChainedProvider`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.features.backends.base import AbstractFlagProvider
from lexigram.features.types import Flag, FlagContext, FlagEvaluation, FlagType


class LocalProvider(AbstractFlagProvider):
    """In-memory provider backed by a ``dict[str, Flag]``.

    Dynamic update methods (:meth:`add_flag`, :meth:`remove_flag`,
    :meth:`set_enabled`) mutate the store safely within a single process.
    """

    def __init__(self, flags: dict[str, Flag] | None = None) -> None:
        self._flags: dict[str, Flag] = dict(flags or {})

    # -- AbstractFlagProvider interface -------------------------------------

    async def get_flag_definition(self, name: str) -> Flag | None:
        """Return the :class:`Flag` definition for *name*, or *None*."""
        return self._flags.get(name)

    async def get_all_flags(self) -> dict[str, Flag]:
        """Return a snapshot copy of all defined flags."""
        return dict(self._flags)

    # -- Synchronous evaluation bridge --------------------------------------

    def evaluate_sync(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Synchronous evaluation — safe because the backing store is in-memory."""
        flag = self._flags.get(name)
        if flag is None:
            return FlagEvaluation(
                flag_name=name,
                enabled=False,
                reason="flag_not_found",
                value=False,
            )
        return self._evaluate_flag(flag, context or FlagContext())

    # -- Mutation helpers ---------------------------------------------------

    def add_flag(self, flag: Flag) -> None:
        """Add or replace a flag definition."""
        flag.updated_at = datetime.now(UTC)
        self._flags[flag.name] = flag

    def remove_flag(self, name: str) -> bool:
        """Remove a flag by name; returns *True* if it existed."""
        return self._flags.pop(name, None) is not None

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Toggle the master enabled switch; returns *True* if the flag exists."""
        if name not in self._flags:
            return False
        self._flags[name].enabled = enabled
        self._flags[name].updated_at = datetime.now(UTC)
        return True

    # -- Convenience helpers (also satisfy MutableFlagProvider protocol) ----

    async def set_flag(self, name: str, value: bool) -> None:
        """Store a boolean flag (async primary)."""
        self.set_flag_sync(name, value)

    def set_flag_sync(self, name: str, value: bool) -> None:
        """Store a boolean flag (sync)."""
        self.add_flag(Flag(name=name, type=FlagType.BOOLEAN, enabled=value))

    async def set_variant(self, name: str, variant: str) -> None:
        """Store a variant flag (async primary)."""
        self.set_variant_sync(name, variant)

    def set_variant_sync(self, name: str, variant: str) -> None:
        """Store a variant flag (sync)."""
        self.add_flag(
            Flag(
                name=name,
                type=FlagType.VARIANT,
                enabled=True,
                default_variant=variant,
            ),
        )

    def clear(self) -> None:
        """Remove all stored flags and variants."""
        self._flags.clear()


__all__ = ["LocalProvider"]
