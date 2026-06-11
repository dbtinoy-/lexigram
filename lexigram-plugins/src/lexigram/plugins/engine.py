"""Boot-time engine that registers enabled entry-point providers.

Consumed by :class:`PluginsModule`. The job that ``discover_providers``
was always documented to perform (``lexigram/app/factory.py``) happens
here, at the container-registration phase, with the admin-toggled
``disabled`` set applied — systemd-preset style: the preset file is read
once at boot, and the effect lasts until the next boot.
"""

from __future__ import annotations

from importlib.metadata import entry_points as _entry_points
from pathlib import Path
from typing import TYPE_CHECKING

from lexigram.contracts.core.constants import EP_PROVIDERS
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger
from lexigram.plugins.state import load_disabled

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)

__all__ = ["PluginEngineProvider"]


class PluginEngineProvider(Provider):
    """Register every enabled ``lexigram.providers`` entry point.

    During ``register()`` the provider scans ``EP_PROVIDERS``, drops every
    entry-point name present in the plugin-state ``disabled`` set, and
    registers each surviving provider with the container registrar,
    mirroring ``MiddlewareProvider``. It tracks the discovered providers
    and drives their ``boot()``/``shutdown()`` lifecycle itself so they
    participate in the application lifecycle without belonging to the
    orchestrator's static list.

    Attributes:
        discovered_providers: Providers instantiated during ``register()``,
            used for lifecycle and by tests.
    """

    name = "plugins"
    priority = ProviderPriority.INFRASTRUCTURE

    def __init__(self, state_path: str | Path | None = None) -> None:
        super().__init__()
        self._state_path = state_path
        self.discovered_providers: list[Provider] = []

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Discover and register enabled providers, skipping the disabled set.

        Args:
            container: The DI container registrar.
        """
        disabled = load_disabled(self._state_path)
        if disabled:
            logger.info(
                "plugins.engine.disabled_at_boot",
                disabled=sorted(disabled),
            )
        for ep in _entry_points(group=EP_PROVIDERS):
            if ep.name in disabled:
                logger.debug("plugins.engine.skipped_disabled", name=ep.name)
                continue
            try:
                provider_cls = ep.load()
            except Exception:  # noqa: BLE001 — skip bad entry points, continue discovery
                logger.warning("plugins.engine.entry_point_load_failed", name=ep.name)
                continue
            if not (isinstance(provider_cls, type) and issubclass(provider_cls, Provider)):
                logger.debug(
                    "plugins.engine.not_a_provider",
                    name=ep.name,
                    loaded=repr(provider_cls),
                )
                continue
            try:
                provider = provider_cls()
            except Exception:  # noqa: BLE001 — skip unconstructible entry points
                logger.debug(
                    "plugins.engine.skipped_ctor",
                    name=ep.name,
                    reason="unconstructible",
                )
                continue
            try:
                await provider.register(container)
            except Exception as exc:  # noqa: BLE001 — third-party provider can raise anything
                logger.warning(
                    "plugins.engine.register_failed",
                    name=ep.name,
                    error=str(exc),
                )
                continue
            self.discovered_providers.append(provider)
            logger.debug("plugins.engine.registered", name=ep.name)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot all discovered providers.

        Args:
            container: The DI container for boot phase.
        """
        for provider in self.discovered_providers:
            await provider.boot(container)

    async def shutdown(self) -> None:
        """Shut down discovered providers in reverse discovery order."""
        for provider in reversed(self.discovered_providers):
            await provider.shutdown()