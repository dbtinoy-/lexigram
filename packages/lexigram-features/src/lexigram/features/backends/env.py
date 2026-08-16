"""Environment-variable-based flag provider.

Reads feature flags from environment variables matching the pattern
``{prefix}{FLAG_NAME}`` where the value encodes the flag type and its
parameters.  The parsed result is cached in-process; call
:meth:`EnvProvider.invalidate` to force a re-read.

Supported value formats:

* ``true`` / ``false`` — :attr:`~lexigram.feature_flags.types.FlagType.BOOLEAN`
* ``percentage:N`` — :attr:`~lexigram.feature_flags.types.FlagType.PERCENTAGE` rollout
* ``users:user1,user2,...`` — :attr:`~lexigram.feature_flags.types.FlagType.USER_LIST`
"""

from __future__ import annotations

import os

from lexigram.features.backends.base import AbstractFlagProvider
from lexigram.features.constants import ENV_PREFIX
from lexigram.features.types import Flag, FlagContext, FlagEvaluation, FlagType


class EnvProvider(AbstractFlagProvider):
    """Feature flag provider that reads from environment variables.

    Flag names are lowercased by stripping the prefix.
    """

    def __init__(self, prefix: str = ENV_PREFIX) -> None:
        self.prefix = prefix
        self._cache: dict[str, Flag] | None = None

    # -- AbstractFlagProvider interface -------------------------------------

    async def get_flag_definition(self, name: str) -> Flag | None:
        """Return the parsed :class:`Flag` for *name*, or *None*."""
        flags = await self.get_all_flags()
        return flags.get(name)

    async def get_all_flags(self) -> dict[str, Flag]:
        """Return all flags parsed from the current environment."""
        if self._cache is not None:
            return self._cache
        flags: dict[str, Flag] = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                flag_name = key[len(self.prefix) :].lower()
                flag = self._parse_flag(flag_name, value.strip())
                if flag is not None:
                    flags[flag_name] = flag
        self._cache = flags
        return flags

    # -- Synchronous bridge -------------------------------------------------

    def evaluate_sync(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Synchronous evaluation using the last-loaded env snapshot."""
        flags = self._cache or {}
        flag = flags.get(name)
        if flag is None:
            return FlagEvaluation(
                flag_name=name,
                enabled=False,
                reason="flag_not_found",
                value=False,
            )
        return self._evaluate_flag(flag, context or FlagContext())

    def invalidate(self) -> None:
        """Discard the cached snapshot so the next read re-reads env vars."""
        self._cache = None

    # -- Parsing ------------------------------------------------------------

    def _parse_flag(self, name: str, raw: str) -> Flag | None:
        """Parse a raw environment variable value into a :class:`Flag`.

        Returns *None* for values that cannot be interpreted.
        """
        lower = raw.lower()

        if lower in ("true", "1", "yes", "on"):
            return Flag(name=name, type=FlagType.BOOLEAN, enabled=True)

        if lower in ("false", "0", "no", "off"):
            return Flag(name=name, type=FlagType.BOOLEAN, enabled=False)

        if lower.startswith("percentage:"):
            try:
                pct = int(lower.split(":", 1)[1])
                return Flag(name=name, type=FlagType.PERCENTAGE, percentage=pct)
            except ValueError:
                return None

        if lower.startswith("users:"):
            user_list = [
                u.strip() for u in raw.split(":", 1)[1].split(",") if u.strip()
            ]
            return Flag(name=name, type=FlagType.USER_LIST, user_list=user_list)

        return None


__all__ = ["EnvProvider"]
