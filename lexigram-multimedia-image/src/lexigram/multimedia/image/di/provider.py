"""DI provider for the image generation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import ImageProvider
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.multimedia.image.config import ImageConfig
from lexigram.multimedia.image.tasks import ImageGenerationTask

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )
    from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

logger = get_logger(__name__)

__all__ = ["ImageGenerationProvider"]


class ImageGenerationProvider(Provider):
    """Provider that registers a configured ImageProvider backend."""

    name = "image"

    def __init__(self, config: ImageConfig | None = None) -> None:
        super().__init__(name="image")
        self._image_config = config or ImageConfig()
        self._backend: ImageProvider | None = None
        self._task_handler: ImageGenerationTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None
        self._credential_resolved: bool = False

    async def _resolve_optional(self, container: Any, protocol: type) -> Any:
        resolver = getattr(container, "resolve_optional", None)
        if resolver is not None:
            return await resolver(protocol)
        try:
            return await container.resolve(protocol)
        except (LookupError, KeyError, ValueError, TypeError):
            return None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._secret_store = await self._resolve_optional(
            container, AsyncSecretStoreProtocol
        )
        self._retry = await self._resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await self._resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._image_config.backend == "local-http":
            from lexigram.multimedia.image.providers.local_http import (
                LocalHttpImageProvider,
            )

            self._backend = cast(
                "ImageProvider",
                LocalHttpImageProvider(
                    base_url=self._image_config.local_http_base_url,
                    timeout=self._image_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._image_config.backend == "stability":
            from lexigram.multimedia.image.providers.stability import (
                StabilityImageProvider,
            )

            api_key = await self._resolve_credential(
                self._image_config.stability_api_key_secret_name
            )
            self._credential_resolved = bool(api_key)
            self._backend = cast(
                "ImageProvider",
                StabilityImageProvider(
                    api_key=api_key or "",
                    timeout=self._image_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._image_config.backend == "openai":
            from lexigram.multimedia.image.providers.openai import OpenAIImageProvider

            api_key = await self._resolve_credential(
                self._image_config.openai_api_key_secret_name
            )
            self._credential_resolved = bool(api_key)
            self._backend = cast(
                "ImageProvider",
                OpenAIImageProvider(
                    api_key=api_key or "",
                    model=self._image_config.openai_model,
                    base_url=self._image_config.openai_base_url,
                    timeout=self._image_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._image_config.backend == "comfyui":
            from lexigram.multimedia.image.providers.comfyui import ComfyUiImageProvider

            self._backend = cast(
                "ImageProvider",
                ComfyUiImageProvider(
                    base_url=self._image_config.comfyui_base_url,
                    checkpoint=self._image_config.comfyui_checkpoint,
                    workflow_path=self._image_config.comfyui_workflow_path,
                    steps=self._image_config.comfyui_steps,
                    cfg_scale=self._image_config.comfyui_cfg_scale,
                    poll_interval=self._image_config.comfyui_poll_interval,
                    timeout=self._image_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
            self._credential_resolved = True
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented image backend: {self._image_config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(ImageProvider, self._backend)

        self._task_handler = ImageGenerationTask(backend=self._backend)
        container.singleton(ImageGenerationTask, self._task_handler)
        logger.info("image_registered", backend=self._image_config.backend)

    async def _resolve_credential(self, secret_name: str) -> str | None:
        """Resolve a provider API key via AsyncSecretStoreProtocol if bound,
        falling back to a plain environment variable when no secret store
        is configured.
        """
        if self._secret_store is not None:
            value = await self._secret_store.get(secret_name)
            if value:
                return value
        import os

        return os.environ.get(secret_name.upper())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        http_backends = {
            "local-http": self._image_config.local_http_base_url,
            "comfyui": self._image_config.comfyui_base_url,
        }
        if self._image_config.backend in http_backends:
            status = await self._check_http_health(
                http_backends[self._image_config.backend], timeout
            )
            return HealthCheckResult(component=self.name, status=status)

        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY
            if self._credential_resolved
            else HealthStatus.DEGRADED,
        )

    async def _check_http_health(self, base_url: str, timeout: float) -> HealthStatus:
        import aiohttp

        endpoint = (
            "/system_stats"
            if base_url == self._image_config.comfyui_base_url
            else "/health"
        )
        try:
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session,
                session.get(f"{base_url}{endpoint}") as resp,
            ):
                return (
                    HealthStatus.HEALTHY
                    if resp.status == 200
                    else HealthStatus.DEGRADED
                )
        except (TimeoutError, OSError, aiohttp.ClientError):
            return HealthStatus.DEGRADED
