"""Features integration — gates UI elements behind feature flags."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class _NoOpFeatures:
    def is_enabled(self, flag: str, context: Any = None) -> bool:
        return True


class FeaturesIntegration:
    """Adapter that checks feature flags for admin UI gating.

    Gracefully no-ops (all flags pass) when ``lexigram-features`` is not
    installed or the integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._flags: Any = _NoOpFeatures()
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import FeaturesIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, FeaturesIntegrationConfig):
            cfg = FeaturesIntegrationConfig()
        if not cfg.enabled:
            self._flags = _NoOpFeatures()
            return
        if not is_installed("lexigram.features"):
            self._flags = _NoOpFeatures()
            return
        self._enabled = True

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        try:
            from lexigram.contracts.feature_flags import FlagManagerProtocol

            self._flags = await container.resolve(FlagManagerProtocol)
        except Exception:  # noqa: BLE001
            self._flags = _NoOpFeatures()

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy"
            if not isinstance(self._flags, _NoOpFeatures)
            else "noop"
        }

    def is_enabled(self, flag: str, context: Any = None) -> bool:
        """Evaluate a synchronous flag provider.

        The canonical feature-flag contract is asynchronous. Callers with a
        real async manager should use :meth:`is_enabled_async`; returning its
        coroutine from this synchronous convenience method would leak an
        unawaited coroutine and make every flag appear truthy.
        """
        if not hasattr(self._flags, "is_enabled"):
            return True
        result = self._flags.is_enabled(flag, context)
        if inspect.isawaitable(result):
            # There is no safe way to block the current event loop here. Keep
            # the documented no-op behavior for sync-only callers and close a
            # coroutine object so Python does not emit a resource warning.
            close = getattr(result, "close", None)
            if close is not None:
                close()
            return True
        return bool(result)

    async def is_enabled_async(self, flag: str, context: Any = None) -> bool:
        """Evaluate either the canonical async provider or a sync provider."""
        if not hasattr(self._flags, "is_enabled"):
            return True
        result = self._flags.is_enabled(flag, context)
        if inspect.isawaitable(result):
            result = await result
        return bool(result)


__all__ = ["FeaturesIntegration"]
