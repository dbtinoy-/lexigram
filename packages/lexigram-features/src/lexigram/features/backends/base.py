"""Abstract base class for rich flag providers.

Defines :class:`AbstractFlagProvider` — an ABC that extends the simple
:class:`~lexigram.contracts.feature_flags.FlagProvider` protocol with a
richer ``evaluate`` coroutine and a complete suite of per-type evaluation
strategy helpers.

Concrete providers (:class:`~lexigram.feature_flags.backends.local.LocalProvider`,
:class:`~lexigram.feature_flags.backends.env.EnvProvider`, etc.) inherit from
this class and override ``get_flag_definition`` and ``get_all_flags``; the
evaluation logic is shared here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
import hashlib
from typing import Any

from lexigram.features.constants import DEFAULT_ENABLED
from lexigram.features.types import (
    Flag,
    FlagContext,
    FlagEvaluation,
    FlagType,
)
from lexigram.logging import get_logger

logger = get_logger(__name__)

_warned_empty_user_attribute_rules: set[str] = set()


class AbstractFlagProvider(ABC):
    """Rich abstract flag provider with full per-type evaluation logic.

    Subclasses must implement :meth:`get_flag_definition` and
    :meth:`get_all_flags`.  All evaluation helpers and the :meth:`evaluate`
    coroutine are provided here.

    This class is *not* a :class:`~lexigram.contracts.feature_flags.FlagProvider`
    protocol implementation — ``get_flag_definition`` returns a
    :class:`~lexigram.feature_flags.types.Flag` model, not a bare boolean.
    Use :class:`~lexigram.features.backends.local.LocalProvider`
    when you only need the simple boolean protocol.
    """

    # ------------------------------------------------------------------
    # Abstract interface — subclasses must implement these two methods.
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_flag_definition(self, name: str) -> Flag | None:
        """Return the full :class:`Flag` definition or *None* if not found."""

    @abstractmethod
    async def get_all_flags(self) -> dict[str, Flag]:
        """Return all known flag definitions keyed by flag name."""

    # ------------------------------------------------------------------
    # Primary public API
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Evaluate flag *name* for *context* and return a :class:`FlagEvaluation`.

        Returns a ``flag_not_found`` evaluation (``enabled=False``) when the
        flag does not exist, so callers can safely treat unknown flags the same
        as disabled ones.
        """
        flag = await self.get_flag_definition(name)
        if flag is None:
            return FlagEvaluation(
                flag_name=name,
                enabled=False,
                reason="flag_not_found",
                value=False,
            )
        return self._evaluate_flag(flag, context or FlagContext())

    def evaluate_sync(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Synchronous evaluation — only valid when the store is in-memory.

        Subclasses that back their data with a sync structure should override
        this if they need to avoid the event loop.  The default raises
        ``NotImplementedError`` to prevent accidental blocking I/O.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support synchronous evaluation",
        )

    # ------------------------------------------------------------------
    # FlagProvider protocol bridge
    # ------------------------------------------------------------------

    async def get_flag(
        self,
        name: str,
        *,
        default: bool = False,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Asynchronous boolean access (primary) — delegates to evaluate."""
        ctx = _dict_to_context(context)
        result = await self.evaluate(name, ctx)
        if result.reason == "flag_not_found":
            return default
        return result.enabled

    def get_flag_sync(
        self,
        name: str,
        *,
        default: bool = False,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Synchronous boolean access — delegates to evaluate_sync."""
        ctx = _dict_to_context(context)
        try:
            result = self.evaluate_sync(name, ctx)
        except NotImplementedError:
            return default

        if result.reason == "flag_not_found":
            return default
        return result.enabled

    async def get_variant(
        self,
        name: str,
        *,
        default: str = "",
        context: dict[str, Any] | None = None,
    ) -> str:
        """Asynchronous variant access (primary) — delegates to evaluate."""
        ctx = _dict_to_context(context)
        result = await self.evaluate(name, ctx)
        if result.reason == "flag_not_found":
            return default
        if isinstance(result.value, str):
            return result.value
        return default

    def get_variant_sync(
        self,
        name: str,
        *,
        default: str = "",
        context: dict[str, Any] | None = None,
    ) -> str:
        """Synchronous variant access — delegates to evaluate_sync."""
        ctx = _dict_to_context(context)
        try:
            result = self.evaluate_sync(name, ctx)
        except NotImplementedError:
            return default
        if isinstance(result.value, str):
            return result.value
        return default

    # ------------------------------------------------------------------
    # Per-type evaluation helpers — shared by all concrete providers.
    # ------------------------------------------------------------------

    def _evaluate_flag(self, flag: Flag, context: FlagContext) -> FlagEvaluation:
        """Dispatch evaluation based on flag type."""
        if not flag.enabled:
            return FlagEvaluation(
                flag_name=flag.name,
                enabled=False,
                reason="flag_disabled",
                value=False,
            )

        dispatch = {
            FlagType.BOOLEAN: self._evaluate_boolean,
            FlagType.PERCENTAGE: self._evaluate_percentage,
            FlagType.USER_LIST: self._evaluate_user_list,
            FlagType.USER_ATTRIBUTE: self._evaluate_user_attribute,
            FlagType.TIME_BASED: self._evaluate_time_based,
            FlagType.VARIANT: self._evaluate_variant,
        }
        handler = dispatch.get(flag.type)
        if handler is None:
            return FlagEvaluation(
                flag_name=flag.name,
                enabled=False,
                reason=f"unsupported_type:{flag.type}",
                value=False,
            )
        return handler(flag, context)

    def _evaluate_boolean(self, flag: Flag, context: FlagContext) -> FlagEvaluation:
        """Evaluate a simple boolean flag."""
        return FlagEvaluation(
            flag_name=flag.name,
            enabled=flag.enabled,
            reason="boolean",
            value=flag.enabled,
        )

    def _evaluate_percentage(self, flag: Flag, context: FlagContext) -> FlagEvaluation:
        """Evaluate a percentage-rollout flag.

        Hash is computed from ``{user_id}:{flag_name}`` so each flag produces
        an independent, deterministic assignment per user.
        """
        bucket_input = f"{context.user_id or ''}:{flag.name}"
        bucket = (
            int(
                hashlib.md5(bucket_input.encode(), usedforsecurity=False).hexdigest(),
                16,
            )
            % 100
        )
        enabled = bucket < flag.percentage
        return FlagEvaluation(
            flag_name=flag.name,
            enabled=enabled,
            reason="percentage_rollout",
            value=enabled,
        )

    def _evaluate_user_list(self, flag: Flag, context: FlagContext) -> FlagEvaluation:
        """Evaluate a flag restricted to an explicit user-ID list."""
        enabled = context.user_id is not None and context.user_id in flag.user_list
        return FlagEvaluation(
            flag_name=flag.name,
            enabled=enabled,
            reason="user_list",
            value=enabled,
        )

    def _evaluate_user_attribute(
        self,
        flag: Flag,
        context: FlagContext,
    ) -> FlagEvaluation:
        """Evaluate a flag gate by matching all required user attribute pairs.

        An empty rule set evaluates disabled (fail-closed) because an
        unconfigured rule is a misconfiguration, not a grant-all.
        """
        if not flag.user_attributes:
            if flag.name not in _warned_empty_user_attribute_rules:
                _warned_empty_user_attribute_rules.add(flag.name)
                logger.warning(
                    "user_attribute_empty_rule_denied",
                    flag=flag.name,
                )
            return FlagEvaluation(
                flag_name=flag.name,
                enabled=DEFAULT_ENABLED,
                reason="user_attribute_empty_rule_denied",
                value=DEFAULT_ENABLED,
            )
        attrs = context.user_attributes or {}
        enabled = all(attrs.get(k) == v for k, v in flag.user_attributes.items())
        return FlagEvaluation(
            flag_name=flag.name,
            enabled=enabled,
            reason="user_attribute",
            value=enabled,
        )

    def _evaluate_time_based(self, flag: Flag, context: FlagContext) -> FlagEvaluation:
        """Evaluate a time-windowed flag against UTC now (or context timestamp)."""
        if context.timestamp is not None:
            now = datetime.fromtimestamp(context.timestamp, tz=UTC)
        else:
            now = datetime.now(UTC)

        after_start = flag.start_time is None or now >= flag.start_time
        before_end = flag.end_time is None or now <= flag.end_time
        enabled = after_start and before_end

        return FlagEvaluation(
            flag_name=flag.name,
            enabled=enabled,
            reason="time_based",
            value=enabled,
        )

    def _evaluate_variant(self, flag: Flag, context: FlagContext) -> FlagEvaluation:
        """Assign a variant deterministically using weighted bucket hashing.

        Variants are sorted by name for deterministic ordering, then a
        cumulative weight range is used to pick the variant for this user.
        """
        if not flag.variants:
            variant = flag.default_variant or ""
            return FlagEvaluation(
                flag_name=flag.name,
                enabled=bool(variant),
                reason="variant_no_config",
                value=variant or False,
            )

        bucket_input = f"{context.user_id or ''}:{flag.name}"
        bucket = (
            int(
                hashlib.md5(bucket_input.encode(), usedforsecurity=False).hexdigest(),
                16,
            )
            % 100
        )

        cumulative = 0
        chosen: str | None = None
        for variant_name in sorted(flag.variants):
            cumulative += flag.variants[variant_name]
            if bucket < cumulative:
                chosen = variant_name
                break

        if chosen is None:
            chosen = flag.default_variant or next(iter(sorted(flag.variants)), "")

        return FlagEvaluation(
            flag_name=flag.name,
            enabled=True,
            reason="variant",
            value=chosen,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dict_to_context(d: dict[str, Any] | None) -> FlagContext | None:
    """Convert a plain dict context to a :class:`FlagContext` if given."""
    if d is None:
        return None
    return FlagContext(
        user_id=d.get("user_id"),
        user_attributes=d.get("user_attributes"),
        session_id=d.get("session_id"),
        request_id=d.get("request_id"),
        timestamp=d.get("timestamp"),
        custom={
            k: v
            for k, v in d.items()
            if k
            not in {
                "user_id",
                "user_attributes",
                "session_id",
                "request_id",
                "timestamp",
            }
        }
        or None,
    )


__all__ = ["AbstractFlagProvider"]
