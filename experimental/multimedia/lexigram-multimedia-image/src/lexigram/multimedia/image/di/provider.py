"""DI provider for the image generation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.protocols import ImageProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.image.backends.registry import ImageBackendRegistry
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
    config_key: str | None = "multimedia_image"
    config_model: type | None = ImageConfig

    def __init__(
        self,
        config: ImageConfig | None = None,
        *,
        backend_registry: ImageBackendRegistry | None = None,
    ) -> None:
        super().__init__(name="image")
        self._requested_config = config
        self._config = config
        self._backend_registry = (
            backend_registry or ImageBackendRegistry.with_defaults()
        )
        self._backend: ImageProvider | None = None
        self._task_handler: ImageGenerationTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._config = self._requested_config or self._config or ImageConfig()
        container.singleton(ImageConfig, self._config)

        self._secret_store = await resolve_optional(container, AsyncSecretStoreProtocol)
        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        self._backend = cast(
            "ImageProvider",
            await self._backend_registry.create_backend(
                self._config.backend,
                self._config,
                self._secret_store,
                self._retry,
                self._circuit_breaker,
            ),
        )

        assert self._backend is not None  # noqa: S101
        container.singleton(ImageProvider, self._backend)

        self._task_handler = ImageGenerationTask(backend=self._backend)
        container.singleton(ImageGenerationTask, self._task_handler)
        logger.info("image_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        http_backends = {
            "local-http": self._config.local_http_base_url,
            "comfyui": self._config.comfyui_base_url,
        }
        if self._config.backend in http_backends:
            status = await self._check_http_health(
                http_backends[self._config.backend], timeout
            )
            return HealthCheckResult(component=self.name, status=status)

        return HealthCheckResult(component=self.name, status=HealthStatus.HEALTHY)

    async def _check_http_health(self, base_url: str, timeout: float) -> HealthStatus:
        import aiohttp

        endpoint = (
            "/system_stats" if base_url == self._config.comfyui_base_url else "/health"
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
