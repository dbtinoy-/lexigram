"""BuilderProvider — registers builder configuration in the container."""

from __future__ import annotations

from typing import Any

from lexigram.builder.config import BuilderConfig
from lexigram.contracts.core.di import BootContainerProtocol, ContainerRegistrarProtocol
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

__all__ = ["BuilderProvider"]


class BuilderProvider(Provider):
    """Registers the builder configuration singleton.

    Args:
        config: Explicit configuration override. When omitted, the
            framework injects the ``builder`` YAML section (via
            ``config_key``/``config_model``) or defaults apply.
    """

    config_key: str | None = BuilderConfig.config_section
    config_model = BuilderConfig

    def __init__(self, config: BuilderConfig | None = None, **kwargs: Any) -> None:
        super().__init__(name="builder", priority=ProviderPriority.APPLICATION)
        self._explicit_config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(BuilderConfig, self._resolve_config())

    async def boot(self, container: BootContainerProtocol) -> None:
        return None

    def _resolve_config(self) -> BuilderConfig:
        if self._explicit_config is not None:
            return self._explicit_config
        return BuilderConfig.from_env()
