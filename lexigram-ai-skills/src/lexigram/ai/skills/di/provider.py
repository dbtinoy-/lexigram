"""SkillsProvider — DI provider registering the skills subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.skills.config import SkillsConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
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

_BUILTIN_MAP: dict[str, str] = {
    "current_datetime": "lexigram.ai.skills.builtin.datetime_skill.DateTimeSkill",
    "math_calculate": "lexigram.ai.skills.builtin.math_skill.MathSkill",
    "text_summarize": "lexigram.ai.skills.builtin.text_processing.TextSummarizeSkill",
    "text_translate": "lexigram.ai.skills.builtin.text_processing.TextTranslateSkill",
    "web_search": "lexigram.ai.skills.builtin.web_search.WebSearchSkill",
    "http_request": "lexigram.ai.skills.builtin.http_request.HTTPRequestSkill",
    "file_read": "lexigram.ai.skills.builtin.file_operations.FileReadSkill",
    "file_write": "lexigram.ai.skills.builtin.file_operations.FileWriteSkill",
    "code_execute": "lexigram.ai.skills.builtin.code_execution.CodeExecutionSkill",
}


def _import_class(dotted_path: str) -> type[Any]:
    """Import a class from a fully qualified dotted path."""
    import importlib

    module_path, _, class_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class SkillsProvider(Provider):
    """Register and bootstrap the skills subsystem."""

    name = "skills"
    priority = ProviderPriority.DOMAIN

    def __init__(
        self,
        config: SkillsConfig | None = None,
        enable_tool_bridge: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialise the provider with optional configuration.

        Args:
            config: Skills configuration. Defaults to ``SkillsConfig()``.
            enable_tool_bridge: Register the tool-bridge adapter so agent tool
                registries can invoke skills as first-class tools.
            **kwargs: Reserved for future keyword arguments.
        """
        super().__init__()
        self._config = config or SkillsConfig()
        self._enable_tool_bridge = enable_tool_bridge

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register all skills services into the container."""
        from lexigram.ai.skills.caching.skill_cache import SkillResultCache
        from lexigram.ai.skills.executor import SkillExecutor
        from lexigram.ai.skills.permissions.permission_checker import PermissionChecker
        from lexigram.ai.skills.registry import SkillRegistry

        container.singleton(SkillsConfig, instance=self._config)
        registry = SkillRegistry()
        container.singleton(SkillRegistry, instance=registry)
        logger.debug("skills_provider_registered", service="SkillRegistry")

        cache: SkillResultCache | None = None
        if self._config.cache_enabled:
            cache = SkillResultCache(ttl_seconds=self._config.cache_ttl_seconds)
            container.singleton(SkillResultCache, instance=cache)
            logger.debug("skills_provider_registered", service="SkillResultCache")

        permission_checker: PermissionChecker | None = None
        if self._config.enforce_permissions:
            permission_checker = PermissionChecker()
            container.singleton(PermissionChecker, instance=permission_checker)
            logger.debug("skills_provider_registered", service="PermissionChecker")

        executor = SkillExecutor(
            registry=registry,
            cache=cast("CacheBackendProtocol | None", cache),
            permission_checker=permission_checker,
        )
        container.singleton(SkillExecutor, instance=executor)
        logger.debug("skills_provider_registered", service="SkillExecutor")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Register built-in and auto-discovered skills into the registry."""
        from lexigram.ai.skills.registry import SkillRegistry

        registry = await container.resolve_optional(SkillRegistry)
        if registry is None:
            logger.warning("skills_registry_not_available")
            return

        if self._config.enable_builtin:
            for skill_name in self._config.builtin_skills:
                dotted = _BUILTIN_MAP.get(skill_name)
                if dotted is None:
                    logger.warning("skills_unknown_builtin", skill=skill_name)
                    continue
                try:
                    cls = _import_class(dotted)
                    registry.register(cls())
                    logger.debug("skills_builtin_registered", skill=skill_name)
                except (
                    ImportError,
                    AttributeError,
                    TypeError,
                    ValueError,
                ) as exc:
                    logger.warning(
                        "skills_builtin_register_error",
                        skill=skill_name,
                        error=str(exc),
                    )

        if self._config.auto_discover:
            from lexigram.ai.skills.discovery.module_scanner import ModuleScanner

            scanner = ModuleScanner()
            for pkg in self._config.scan_packages:
                try:
                    count = await scanner.scan_package(registry, pkg)
                    logger.info("skills_auto_discovered", package=pkg, count=count)
                except (
                    ImportError,
                    AttributeError,
                    RuntimeError,
                    ValueError,
                ) as exc:
                    logger.warning(
                        "skills_discovery_error", package=pkg, error=str(exc)
                    )

        # Skill sources (SKILL.md files from various directories)
        if self._config.enable_skill_sources:
            from lexigram.ai.skills.discovery.skill_loader import SkillLoader
            from lexigram.ai.skills.discovery.skill_source_scanner import (
                SkillSourceScanner,
            )

            loader = SkillLoader(
                timeout_seconds=self._config.script_timeout_seconds,
            )
            source_scanner = SkillSourceScanner(loader=loader)

            # Scan all configured paths
            for path_str in self._config.skill_paths:
                path = Path(path_str).expanduser()
                if not path.exists():
                    logger.debug("skill_source_path_not_found", path=path_str)
                    continue

                try:
                    count = await source_scanner.scan(registry, str(path))
                    logger.info("skill_sources_discovered", path=path_str, count=count)
                except Exception as exc:  # noqa: BLE001  # skill source scanning is best-effort; one failure must not stop others
                    logger.warning(
                        "skill_source_discovery_error",
                        path=path_str,
                        error=str(exc),
                    )

    async def shutdown(self) -> None:
        """Perform any cleanup on shutdown (no-op for the skills provider)."""

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


__all__ = ["SkillsProvider"]
