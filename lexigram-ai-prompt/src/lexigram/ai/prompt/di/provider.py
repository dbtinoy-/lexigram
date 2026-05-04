"""Prompt DI provider — registers the PromptRegistry and PromptService with the container."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.assembly.assembler import CacheAwarePromptAssembler
from lexigram.ai.prompt.assembly.cache_strategies import ProviderCacheStrategyRegistry
from lexigram.ai.prompt.config import PromptConfig
from lexigram.ai.prompt.registry.registry import PromptRegistry
from lexigram.ai.prompt.rendering.sanitizer import InputSanitizer
from lexigram.ai.prompt.service.loader import DictPromptLoader, DirectoryPromptLoader
from lexigram.ai.prompt.service.models import PromptTemplate
from lexigram.ai.prompt.service.observer import PromptObserverProtocol
from lexigram.ai.prompt.service.service import PromptService, PromptServiceProtocol
from lexigram.contracts.ai.llm import PromptAssemblerProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.hooks import HookRegistryProtocol
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.contracts.exceptions.provider import ModuleVisibilityError
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class PromptProvider(Provider):
    """Provider for the prompt registry and prompt service.

    Reads :class:`~lexigram.ai.prompt.config.PromptConfig`, builds a
    :class:`~lexigram.ai.prompt.registry.registry.PromptRegistry` and a
    :class:`~lexigram.ai.prompt.service.service.PromptService`, and registers
    both as singletons.

    The ``PromptService`` is configured via the keyword arguments:

    * ``template_dir`` — path to a directory of YAML/JSON template files.
    * ``inline_templates`` — list of raw template dicts (see
      :class:`~lexigram.ai.prompt.service.loader.DictPromptLoader`).
    * ``observer`` — an object implementing
      :class:`~lexigram.ai.prompt.service.observer.PromptObserverProtocol`.

    At least one of ``template_dir`` or ``inline_templates`` may be supplied;
    both are combined if provided.  When neither is supplied the
    ``PromptService`` starts empty (useful in tests).
    """

    name = "prompt"
    priority = ProviderPriority.DOMAIN

    def __init__(
        self,
        config: PromptConfig | None = None,
        *,
        template_dir: str | Path | None = None,
        inline_templates: list[dict[str, Any]] | None = None,
        observer: PromptObserverProtocol | None = None,
    ) -> None:
        """Initialize with optional config and template sources.

        Args:
            config: Optional :class:`~lexigram.ai.prompt.config.PromptConfig`.
            template_dir: Optional path to a directory of YAML/JSON files.
            inline_templates: Optional list of raw template dicts.
            observer: Optional observability hook for ``PromptService``.
        """
        super().__init__()
        self._config = config or PromptConfig()
        self._template_dir = Path(template_dir) if template_dir else None
        self._inline_templates: list[dict[str, Any]] = inline_templates or []
        self._observer = observer

    def _load_templates(self) -> list[PromptTemplate]:
        """Load all templates from configured sources."""
        templates: list[PromptTemplate] = []

        if self._template_dir is not None:
            templates.extend(
                DirectoryPromptLoader(
                    self._template_dir, default_format=self._config.default_format
                ).load()
            )

        if self._inline_templates:
            templates.extend(
                DictPromptLoader(
                    self._inline_templates, default_format=self._config.default_format
                ).load()
            )

        return templates

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the PromptConfig, PromptRegistry, PromptService, and CacheAwarePromptAssembler."""
        container.singleton(PromptConfig, self._config)

        if not self._config.enabled:
            logger.info("prompt_disabled", reason="PromptConfig.enabled=False")
            return

        registry = PromptRegistry()
        container.singleton(PromptRegistry, registry)

        # Register PromptService with loaded templates
        templates = self._load_templates()
        sanitizer: InputSanitizer | None = None
        if self._config.sanitize_inputs:
            sanitizer = InputSanitizer(strict=self._config.strict_sanitizer)
        service = PromptService(
            templates=templates,
            observer=self._observer,
            sanitizer=sanitizer,
        )
        container.singleton(PromptService, service)
        container.singleton(PromptServiceProtocol, service)

        # Register cache-aware assembler components
        strategy_registry = ProviderCacheStrategyRegistry.with_defaults()
        container.singleton(ProviderCacheStrategyRegistry, strategy_registry)

        # Create assembler without token counter initially — will be enhanced in boot()
        assembler = CacheAwarePromptAssembler(
            strategy_registry=strategy_registry,
            token_counter=None,
        )
        container.singleton(PromptAssemblerProtocol, assembler)

        logger.info(
            "prompt_provider_registered",
            format=self._config.default_format,
            sanitize_inputs=self._config.sanitize_inputs,
            service_templates=len(templates),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase — inject optional TokenCounterProtocol and hook registry."""
        hook_registry = await container.resolve_optional(HookRegistryProtocol)
        service = await container.resolve(PromptService)
        service.attach_hook_registry(hook_registry)

        try:
            from lexigram.contracts.ai.llm import TokenCounterProtocol

            token_counter = await container.resolve(TokenCounterProtocol)
            assembler = await container.resolve(PromptAssemblerProtocol)
            if isinstance(assembler, CacheAwarePromptAssembler):
                assembler.set_token_counter(token_counter)
                logger.debug("prompt_assembler_token_counter_injected")
            else:
                logger.warning(
                    "prompt_assembler_token_counter_skipped",
                    assembler_type=type(assembler).__name__,
                )
        except (UnresolvableDependencyError, ModuleVisibilityError):
            logger.debug("prompt_assembler_token_counter_unavailable")

        logger.debug("prompt_provider_booted")

    async def shutdown(self) -> None:
        """Shutdown phase — no cleanup required for prompt registry."""
        logger.debug("prompt_provider_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process domain provider).

        No external backend to ping.

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to ping.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )
