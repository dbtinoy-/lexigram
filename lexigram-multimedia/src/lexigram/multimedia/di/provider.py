"""Umbrella DI provider — orchestrates the 4 core multimedia sub-providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.multimedia.config import MultimediaConfig

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
    from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol

logger = get_logger(__name__)

__all__ = ["MultimediaProvider"]

_CORE_SUBSYSTEMS = ("audio-tts", "audio-music", "video", "image")


class MultimediaProvider(Provider):
    """Provider that registers all four core multimedia sub-providers.

    Hardcodes wiring of the 4 core siblings (matching AIProvider.register()'s
    treatment of llm/vector/rag) rather than relying purely on entry-point
    discovery — each needs its own typed config sub-object from
    MultimediaConfig, which a generic entry-point loop can't supply.
    """

    name = "multimedia"

    def __init__(self, config: MultimediaConfig | None = None) -> None:
        super().__init__(name="multimedia")
        self._multimedia_config = config or MultimediaConfig()
        self._sub_providers: dict[str, Any] = {}
        self._storage: BlobStoreProtocol | None = None
        self._cache_backend: CacheBackendProtocol | None = None
        self._task_manager: Any | None = None
        self._idempotency_manager: Any | None = None
        self._event_bus: Any | None = None
        self._wrapped_task_handlers: dict[str, Any] = {}

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.multimedia.audio_music.di.provider import AudioMusicProvider
        from lexigram.multimedia.audio_tts.di.provider import AudioTTSProvider
        from lexigram.multimedia.image.di.provider import ImageGenerationProvider
        from lexigram.multimedia.video.di.provider import VideoGenerationProvider

        self._sub_providers["audio-tts"] = AudioTTSProvider(config=self._multimedia_config.tts)
        self._sub_providers["audio-music"] = AudioMusicProvider(
            config=self._multimedia_config.music
        )
        self._sub_providers["video"] = VideoGenerationProvider(
            config=self._multimedia_config.video
        )
        self._sub_providers["image"] = ImageGenerationProvider(
            config=self._multimedia_config.image
        )
        for sub in self._sub_providers.values():
            await sub.register(container)

        # ------------------------------------------------------------------
        # Entry-point discovery for additional multimedia subsystems beyond
        # the 4 core ones. Mirrors AIProvider.register()'s
        # "lexigram.ai.subsystems" loop, including skipping the core names.
        # ------------------------------------------------------------------
        try:
            from importlib.metadata import entry_points as _entry_points

            for _ep in _entry_points(group="lexigram.multimedia.subsystems"):
                if _ep.name in _CORE_SUBSYSTEMS:
                    continue
                _provider_cls = _ep.load()
                _sub_provider = _provider_cls()
                await _sub_provider.register(container)
                self._sub_providers[_ep.name] = _sub_provider
                logger.info(
                    "multimedia_subsystem_registered_via_entry_point",
                    subsystem=_ep.name,
                )
        except ImportError:
            logger.debug("importlib.metadata unavailable; skipping subsystem discovery")

        logger.info("multimedia_services_registered", subsystems=list(self._sub_providers))

    async def boot(self, container: ContainerResolverProtocol) -> None:
        # BlobStoreProtocol and other peer-provider singletons are resolved
        # here, not in register(). Application.start() runs "register all
        # providers" as its own phase before "boot all providers" — so
        # during register(), lexigram-storage's provider may not have bound
        # BlobStoreProtocol yet, regardless of app.use() call order. See
        # lexigram/src/lexigram/app/base.py's two-phase startup lifecycle.
        from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
        from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol

        try:
            self._storage = await container.resolve(BlobStoreProtocol)
        except (LookupError, KeyError, ValueError, TypeError):
            self._storage = None
            logger.warning(
                "multimedia_no_storage_bound",
                reason="BlobStoreProtocol not resolvable — submit() will fail for "
                "any provider that returns raw bytes until lexigram-storage is configured",
            )

        try:
            self._cache_backend = await container.resolve(CacheBackendProtocol)
        except (LookupError, KeyError, ValueError, TypeError):
            self._cache_backend = None
            logger.debug("multimedia_no_cache_backend_bound; result caching disabled")

    async def shutdown(self) -> None:
        for sub in self._sub_providers.values():
            shutdown = getattr(sub, "shutdown", None)
            if shutdown is not None:
                await shutdown()
        self._sub_providers.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        details: dict[str, Any] = {"components": {}}
        overall = HealthStatus.HEALTHY
        for name, sub in self._sub_providers.items():
            sub_result = await sub.health_check(timeout=timeout)
            details["components"][name] = sub_result.to_dict()
            if sub_result.status != HealthStatus.HEALTHY:
                overall = HealthStatus.DEGRADED
        return HealthCheckResult(component=self.name, status=overall, details=details)

    @property
    def tts(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["audio-tts"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="tts_generation",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}tts/",
            idempotency_manager=self._idempotency_manager,
        )

    @property
    def music(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["audio-music"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="music_generation",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}music/",
            idempotency_manager=self._idempotency_manager,
        )

    @property
    def video(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["video"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="video_generation",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}video/",
            idempotency_manager=self._idempotency_manager,
        )

    @property
    def image(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["image"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="image_generation",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}image/",
            idempotency_manager=self._idempotency_manager,
        )
