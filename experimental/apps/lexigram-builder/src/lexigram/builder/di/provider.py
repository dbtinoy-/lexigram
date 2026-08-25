"""BuilderProvider — registers builder configuration and services."""

from __future__ import annotations

from typing import Any

from lexigram.builder.config import BuilderConfig
from lexigram.builder.services.generation import GenerationService
from lexigram.builder.services.preview import PreviewService
from lexigram.builder.services.projects import ProjectService
from lexigram.contracts.core.di import BootContainerProtocol, ContainerRegistrarProtocol
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

__all__ = ["BuilderProvider"]


class BuilderProvider(Provider):
    """Registers the builder configuration and service singletons.

    Args:
        config: Explicit configuration override. When omitted, the
            framework injects the ``builder`` YAML section (via
            ``config_key``/``config_model``) or defaults apply.
        projects: Optional pre-built ProjectService (tests).
        previews: Optional pre-built PreviewService (tests).
        generations: Optional pre-built GenerationService (tests).
    """

    config_key: str | None = BuilderConfig.config_section
    config_model = BuilderConfig

    def __init__(
        self,
        config: BuilderConfig | None = None,
        *,
        projects: ProjectService | None = None,
        previews: PreviewService | None = None,
        generations: GenerationService | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="builder", priority=ProviderPriority.APPLICATION)
        self._explicit_config = config
        self._projects = projects
        self._previews = previews
        self._generations = generations

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.builder.services.runtime import (
            AsyncSubprocessRunner,
            UvicornSpawner,
            default_projects_root,
            httpx_health_check,
        )

        config = self._resolve_config()
        container.singleton(BuilderConfig, config)

        default_root = default_projects_root().parent
        projects = self._projects or ProjectService(
            config.resolved_projects_dir(default_root)
        )
        container.singleton(ProjectService, projects)

        previews = self._previews or PreviewService(
            UvicornSpawner(), health_check=httpx_health_check
        )
        container.singleton(PreviewService, previews)

        generations = self._generations or GenerationService(
            projects,
            previews,
            AsyncSubprocessRunner(),
            writer=None,
        )
        container.singleton(GenerationService, generations)

    async def boot(self, container: BootContainerProtocol) -> None:
        return None

    def _resolve_config(self) -> BuilderConfig:
        if self._explicit_config is not None:
            return self._explicit_config
        return BuilderConfig.from_env()
