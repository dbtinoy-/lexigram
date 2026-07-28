"""Layered provider that queries multiple providers in order.

The first provider that returns a non-*None* flag definition wins.
This allows environment overrides to take precedence over code-defined
defaults without modifying either provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.features.backends.base import AbstractFlagProvider

if TYPE_CHECKING:
    from lexigram.features.types import Flag


class ChainedProvider(AbstractFlagProvider):
    """Layered provider that queries multiple providers in order.

    The first provider that returns a non-*None* flag definition wins.
    When merging all flags, earlier providers take precedence over later ones.
    """

    def __init__(self, providers: list[AbstractFlagProvider]) -> None:
        self._providers = providers

    # -- AbstractFlagProvider interface -------------------------------------

    async def get_flag_definition(self, name: str) -> Flag | None:
        """Return the first match across the provider chain, or *None*."""
        for provider in self._providers:
            flag = await provider.get_flag_definition(name)
            if flag is not None:
                return flag
        return None

    async def get_all_flags(self) -> dict[str, Flag]:
        """Merge flags from all providers; earlier providers take precedence."""
        merged: dict[str, Flag] = {}
        # iterate in reverse so highest-priority providers overwrite
        for provider in reversed(self._providers):
            merged.update(await provider.get_all_flags())
        return merged


__all__ = ["ChainedProvider"]
