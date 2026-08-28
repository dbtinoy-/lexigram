"""Central feature flag manager implementation.

:class:`FlagManager` is the primary entry point for evaluating feature flags
in application code. It wraps any :class:`~lexigram.features.backends.base.AbstractFlagProvider`
and adds in-process TTL caching, runtime overrides, change listeners, variant
support, and a configurable default-enabled fallback.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import time
from typing import TYPE_CHECKING, Any

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.features.backends.chained import ChainedProvider
from lexigram.features.backends.local import LocalProvider
from lexigram.features.types import FlagContext, FlagEvaluation
from lexigram.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.contracts.events.protocols import EventBusProtocol
    from lexigram.features.backends.base import AbstractFlagProvider
    from lexigram.features.manager.types import (
        AsyncFlagChangeListener,
        FlagChangeListener,
    )


@dataclass
class FlagAuditEntry:
    """Records a single flag override change for compliance and observability.

    Attributes:
        flag_name: The name of the feature flag that was changed.
        actor: Optional identifier of the entity that made the change.
        old_value: The override state before the change (``None`` if no prior override).
        new_value: The override state after the change.
        timestamp: UTC datetime when the change was recorded.
    """

    flag_name: str
    actor: str | None
    old_value: bool | None
    new_value: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class FlagManager:
    """Central feature flag manager with caching, overrides, and variant support.

    Wraps an :class:`~lexigram.features.backends.base.AbstractFlagProvider` and
    handles cache invalidation, runtime overrides, and change notification.

    Example::

        provider = LocalProvider({
            "new_checkout": Flag("new_checkout", enabled=True),
        })
        manager = FlagManager(provider, cache_ttl=60)

        ctx = FlagContext(user_id="user-123")
        if await manager.is_enabled("new_checkout", ctx):
            ...
    """

    def __init__(
        self,
        provider: AbstractFlagProvider | None = None,
        *,
        cache_ttl: int = 300,
        default_enabled: bool = False,
        event_bus: EventBusProtocol | None = None,
    ) -> None:
        self._provider: AbstractFlagProvider = provider or LocalProvider()
        # Keep the base provider in a priority-aware chain so ``add_provider``
        # can layer environment, local, or remote definitions without
        # silently discarding flags already configured on the manager.
        self._provider_entries: list[tuple[int, int, AbstractFlagProvider]] = [
            (0, 0, self._provider),
        ]
        self._provider_sequence = 0
        self._cache_ttl = cache_ttl
        self._default_enabled = default_enabled
        self._event_bus: EventBusProtocol | None = event_bus
        self._listeners: list[FlagChangeListener] = []
        self._async_listeners: list[AsyncFlagChangeListener] = []
        self._disabled_flags: set[str] = set()
        self._enabled_flags: set[str] = set()
        self._cache: dict[str, tuple[FlagEvaluation, float]] = {}
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._audit_log: list[FlagAuditEntry] = []

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    async def is_enabled(
        self,
        name: str,
        context: FlagContext | None = None,
        *,
        default: bool | None = None,
    ) -> bool:
        """Return whether *name* is enabled for *context*.

        Runtime overrides take precedence over the provider result.

        Args:
            name: Flag name.
            context: Optional evaluation context.
            default: Override the instance's ``default_enabled`` for this call.

        Returns:
            True if the flag is enabled.
        """
        if name in self._enabled_flags:
            return True
        if name in self._disabled_flags:
            return False

        evaluation = await self.evaluate(name, context)
        if evaluation.reason == "flag_not_found":
            if default is not None:
                return default
            return self._default_enabled
        return evaluation.enabled

    async def evaluate(
        self,
        name: str,
        context: FlagContext | None = None,
    ) -> FlagEvaluation:
        """Evaluate *name* for *context*, using the TTL cache when available.

        Args:
            name: Flag name.
            context: Optional evaluation context.

        Returns:
            A :class:`~lexigram.features.types.FlagEvaluation` result.
        """
        cache_key = self._get_cache_key(name, context)
        if self._cache_ttl > 0 and cache_key in self._cache:
            evaluation, ts = self._cache[cache_key]
            if time.monotonic() - ts < self._cache_ttl:
                return evaluation

        try:
            evaluation = await self._provider.evaluate(name, context)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "flag_provider_error",
                flag=name,
                error=str(exc),
            )
            return FlagEvaluation(
                flag_name=name,
                enabled=self._default_enabled,
                reason="provider_error",
            )

        if self._cache_ttl > 0:
            self._cache[cache_key] = (evaluation, time.monotonic())
        return evaluation

    async def get_variant(
        self,
        name: str,
        context: FlagContext | None = None,
        *,
        default: str = "",
    ) -> str:
        """Return the variant string for a VARIANT-type flag.

        Returns *default* if the flag is not found, disabled, or is not a
        VARIANT flag.

        Args:
            name: Flag name.
            context: Optional evaluation context.
            default: Fallback value when no variant string is available.

        Returns:
            The variant string or *default*.
        """
        evaluation = await self.evaluate(name, context)
        if isinstance(evaluation.value, str):
            return evaluation.value
        return default

    def add_provider(self, provider: AbstractFlagProvider, priority: int = 50) -> None:
        """Register a flag provider at the given priority level.

        Providers are queried from highest to lowest priority. When multiple
        providers define the same flag, the higher-priority definition wins;
        lower-priority providers remain available for flags it does not define.
        Providers with the same priority use most-recently-added precedence.
        """
        self._provider_sequence += 1
        self._provider_entries.append((priority, self._provider_sequence, provider))
        ordered = [
            entry[2]
            for entry in sorted(
                self._provider_entries,
                key=lambda entry: (entry[0], entry[1]),
                reverse=True,
            )
        ]
        self._provider = ordered[0] if len(ordered) == 1 else ChainedProvider(ordered)
        # A new definition may change any cached evaluation, including a
        # previously missing flag, so provider registration invalidates cache.
        self._cache.clear()

    async def get_value(
        self,
        key: str,
        default: object,
        context: FlagContext | None = None,
    ) -> object:
        """Evaluate a feature flag and return its resolved value."""
        from lexigram.features.backends.base import _dict_to_context

        ctx = _dict_to_context(context) if isinstance(context, dict) else context
        evaluation = await self.evaluate(key, ctx)
        if evaluation.reason == "flag_not_found":
            return default
        return (
            evaluation.value
            if hasattr(evaluation, "value") and evaluation.value is not None
            else default
        )

    async def get_all_flags(
        self,
        context: FlagContext | None = None,
    ) -> dict[str, FlagEvaluation]:
        """Return evaluations for all known flags.

        Definitions come from the provider; each is evaluated against
        *context* here so the mapping honours the
        ``dict[str, FlagEvaluation]`` contract instead of leaking raw
        ``Flag`` definitions.
        """
        if not hasattr(self._provider, "get_all_flags"):
            return {}

        definitions: dict[str, Any] = await self._provider.get_all_flags()
        evaluations: dict[str, FlagEvaluation] = {}
        for name in definitions:
            evaluation = await self._provider.evaluate(name, context)
            evaluations[name] = evaluation
        return evaluations

    # ------------------------------------------------------------------
    # Runtime overrides
    # ------------------------------------------------------------------

    def get_override_state(self, name: str) -> bool | None:
        """Return the current runtime override for *name*.

        Returns:
            ``True`` if force-enabled, ``False`` if force-disabled,
            ``None`` if no override is active.
        """
        if name in self._enabled_flags:
            return True
        if name in self._disabled_flags:
            return False
        return None

    def enable(self, name: str, *, actor: str | None = None) -> None:
        """Force-enable *name* regardless of provider result."""
        old_value: bool | None = self.get_override_state(name)
        self._enabled_flags.add(name)
        self._disabled_flags.discard(name)
        self._audit_log.append(
            FlagAuditEntry(
                flag_name=name, actor=actor, old_value=old_value, new_value=True
            )
        )
        self._notify_listeners(name, old_value is True, True, actor=actor)

    def disable(self, name: str, *, actor: str | None = None) -> None:
        """Force-disable *name* regardless of provider result."""
        old_value: bool | None = self.get_override_state(name)
        self._disabled_flags.add(name)
        self._enabled_flags.discard(name)
        self._audit_log.append(
            FlagAuditEntry(
                flag_name=name, actor=actor, old_value=old_value, new_value=False
            )
        )
        self._notify_listeners(name, old_value is True, False, actor=actor)

    def set_override(
        self, name: str, enabled: bool, *, actor: str | None = None
    ) -> None:
        """Convenience wrapper that calls :meth:`enable` or :meth:`disable`."""
        if enabled:
            self.enable(name, actor=actor)
        else:
            self.disable(name, actor=actor)

    def clear_override(self, name: str) -> None:
        """Remove any runtime override for *name*, restoring provider control."""
        self._enabled_flags.discard(name)
        self._disabled_flags.discard(name)

    def get_audit_log(self) -> list[FlagAuditEntry]:
        """Return a copy of all recorded flag change audit entries.

        Each entry captures the flag name, actor, old value, new value, and
        the UTC timestamp of the change.  Entries are ordered oldest-first.

        Returns:
            List of :class:`FlagAuditEntry` instances representing every
            :meth:`enable` / :meth:`disable` / :meth:`set_override` call
            since this manager was created.
        """
        return list(self._audit_log)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    async def clear_cache(self) -> None:
        """Flush all cached evaluations."""
        self._cache.clear()

    def clear_cache_for(self, name: str) -> None:
        """Flush cached evaluations for a single flag name."""
        keys = [k for k in self._cache if k.startswith(f"flag:{name}")]
        for k in keys:
            del self._cache[k]

    def _get_cache_key(self, name: str, context: FlagContext | None) -> str:
        if context is None:
            return f"flag:{name}"
        ctx_hash = context.context_hash()
        if not ctx_hash:
            return f"flag:{name}"
        return f"flag:{name}:ctx:{ctx_hash}"

    # ------------------------------------------------------------------
    # Change listeners
    # ------------------------------------------------------------------

    def add_listener_sync(self, fn: FlagChangeListener) -> None:
        """Register a sync callback invoked when a flag override changes."""
        self._listeners.append(fn)

    def remove_listener_sync(self, fn: FlagChangeListener) -> None:
        """Deregister a previously registered sync listener."""
        self._listeners.remove(fn)

    def add_listener(self, fn: AsyncFlagChangeListener) -> None:
        """Register an async callback invoked when a flag override changes."""
        self._async_listeners.append(fn)

    def remove_listener(self, fn: AsyncFlagChangeListener) -> None:
        """Deregister a previously registered async listener."""
        self._async_listeners.remove(fn)

    def _notify_listeners(
        self,
        name: str,
        old_enabled: bool,
        new_enabled: bool,
        actor: str | None = None,
    ) -> None:
        """Call all sync listeners synchronously; schedule async listeners."""
        for fn in self._listeners:
            fn(name, old_enabled, new_enabled)
        try:
            asyncio.get_running_loop()
            if self._async_listeners:
                for afn in self._async_listeners:
                    create_tracked_task(
                        afn(name, old_enabled, new_enabled),
                        self._background_tasks,
                        name=f"flag_listener_{name}",
                    )
            if self._event_bus is not None:
                from lexigram.features.events import FlagChangeEvent

                event = FlagChangeEvent(
                    flag_name=name,
                    old_enabled=old_enabled,
                    new_enabled=new_enabled,
                    actor=actor,
                )
                create_tracked_task(
                    self._event_bus.publish(event),
                    self._background_tasks,
                    name=f"flag_event_{name}",
                )
        except RuntimeError:
            pass  # No running event loop; async listeners silently skipped.

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def provider(self) -> AbstractFlagProvider:
        """The underlying flag provider instance."""
        return self._provider


__all__ = ["FlagManager"]
