"""Features integration — gates UI elements behind feature flags."""

from __future__ import annotations

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
        self._flags: Any = None
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
        return (
            self._flags.is_enabled(flag, context)
            if hasattr(self._flags, "is_enabled")
            else True
        )

    async def is_enabled_async(self, flag: str, context: Any = None) -> bool:
        return (
            self._flags.is_enabled(flag, context)
            if hasattr(self._flags, "is_enabled")
            else True
        )


__all__ = ["FeaturesIntegration"]
