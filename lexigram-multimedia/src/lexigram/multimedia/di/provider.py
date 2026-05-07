"""Umbrella DI provider — orchestrates the 7 core multimedia sub-providers."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.multimedia.config import MultimediaConfig
from lexigram.multimedia.constants import CORE_SUBSYSTEMS

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
    from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol
    from lexigram.multimedia.accessors import (
        BeatAccessor,
        ComposeAccessor,
        VideoAccessor,
    )
    from lexigram.multimedia.timeline import TimelineRenderTask

logger = get_logger(__name__)

__all__ = ["MultimediaProvider"]


class MultimediaProvider(Provider):
    """Provider that registers all seven core multimedia sub-providers.

    Hardcodes wiring of the 7 core siblings (matching AIProvider.register()'s
    treatment of llm/vector/rag) rather than relying purely on entry-point
    discovery — each needs its own typed config sub-object from
    MultimediaConfig, which a generic entry-point loop can't supply.
    """

    name = "multimedia"
    config_key: str | None = "multimedia"
    config_model: type | None = MultimediaConfig

    def __init__(self, config: MultimediaConfig | None = None) -> None:
        super().__init__(name="multimedia")
        self._requested_config = config
        self._config = config or MultimediaConfig()
        self._sub_providers: dict[str, Any] = {}
        self._storage: BlobStoreProtocol | None = None
        self._cache_backend: CacheBackendProtocol | None = None
        self._task_manager: Any | None = None
        self._idempotency_manager: Any | None = None
        self._event_bus: Any | None = None
        self._wrapped_task_handlers: dict[str, Any] = {}
        self._timeline_task_handler: TimelineRenderTask | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.multimedia.beat.di.provider import BeatAnalysisGenerationProvider
        from lexigram.multimedia.image.di.provider import ImageGenerationProvider
        from lexigram.multimedia.interpolate.di.provider import (
            InterpolationGenerationProvider,
        )
        from lexigram.multimedia.music.di.provider import AudioMusicProvider
        from lexigram.multimedia.tts.di.provider import AudioTTSProvider
        from lexigram.multimedia.upscale.di.provider import UpscaleGenerationProvider
        from lexigram.multimedia.video.di.provider import VideoGenerationProvider

        self._config = self._requested_config or self._config or MultimediaConfig()
        container.singleton(MultimediaConfig, self._config)

        self._sub_providers["tts"] = AudioTTSProvider(config=self._config.tts)
        self._sub_providers["music"] = AudioMusicProvider(config=self._config.music)
        self._sub_providers["video"] = VideoGenerationProvider(
            config=self._config.video
        )
        self._sub_providers["image"] = ImageGenerationProvider(
            config=self._config.image
        )
        self._sub_providers["upscale"] = UpscaleGenerationProvider(
            config=self._config.upscale
        )
        self._sub_providers["interpolate"] = InterpolationGenerationProvider(
            config=self._config.interpolate
        )
        self._sub_providers["beat"] = BeatAnalysisGenerationProvider(
            config=self._config.beat
        )
        for sub in self._sub_providers.values():
            await sub.register(container)

        # ------------------------------------------------------------------
        # Entry-point discovery for additional multimedia subsystems beyond
        # the 7 core ones. Mirrors AIProvider.register()'s
        # "lexigram.ai.subsystems" loop, including skipping the core names.
        # ------------------------------------------------------------------
        try:
            for _ep in importlib.metadata.entry_points(
                group="lexigram.multimedia.subsystems"
            ):
                if _ep.name in CORE_SUBSYSTEMS:
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

        logger.info(
            "multimedia_services_registered", subsystems=list(self._sub_providers)
        )

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
        except (LookupError, KeyError, ValueError, TypeError, UnresolvableDependencyError):
            self._storage = None
            logger.warning(
                "multimedia_no_storage_bound",
                reason="BlobStoreProtocol not resolvable — submit() will fail for "
                "any provider that returns raw bytes until lexigram-storage is configured",
            )

        try:
            self._cache_backend = await container.resolve(CacheBackendProtocol)
        except (LookupError, KeyError, ValueError, TypeError, UnresolvableDependencyError):
            self._cache_backend = None
            logger.debug("multimedia_no_cache_backend_bound; result caching disabled")

        from lexigram.contracts.events.protocols import EventBusProtocol

        try:
            self._event_bus = await container.resolve(EventBusProtocol)
        except (LookupError, KeyError, ValueError, TypeError, UnresolvableDependencyError):
            self._event_bus = None
            logger.debug("multimedia_no_event_bus_bound; generation events disabled")

        await self._wire_task_manager(container)

    async def _wire_task_manager(self, container: ContainerResolverProtocol) -> None:
        from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
        from lexigram.contracts.infra.tasks import TaskQueueProtocol
        from lexigram.multimedia.stores import (
            InMemoryIdempotencyStoreFallback,
        )
        from lexigram.tasks.di.provider import TaskProvider
        from lexigram.tasks.execution.manager import (
            IdempotencyManager,
            IdempotentTaskManager,
        )

        try:
            task_provider = await container.resolve(TaskProvider)
            task_queue = await container.resolve(TaskQueueProtocol)
        except (LookupError, KeyError, ValueError, TypeError, UnresolvableDependencyError):
            logger.warning(
                "multimedia_no_task_provider_bound",
                reason="lexigram-tasks not configured — submit() will be unavailable, "
                "only the synchronous generate() path will work",
            )
            return

        idempotency_store: Any
        try:
            idempotency_store = await container.resolve(IdempotencyStoreProtocol)
        except (LookupError, KeyError, ValueError, TypeError, UnresolvableDependencyError):
            idempotency_store = InMemoryIdempotencyStoreFallback()

        idempotency_manager = IdempotencyManager(storage=idempotency_store)
        self._idempotency_manager = idempotency_manager
        self._task_manager = IdempotentTaskManager(
            queue_client=task_queue, idempotency_manager=idempotency_manager
        )

        import uuid

        from lexigram.multimedia.storage import normalize_asset_dict

        class _WrappedTaskHandler:
            def __init__(self, inner: Any, storage: Any, path_prefix: str) -> None:
                self._inner = inner
                self._storage = storage
                self._path_prefix = path_prefix

            async def run(self, params: dict[str, Any]) -> dict[str, Any]:
                asset_dict: dict[str, Any] = await self._inner.run(params)
                if self._storage is None:
                    return asset_dict
                ext = asset_dict.get("mime_type", "application/octet-stream").split(
                    "/"
                )[-1]
                return await normalize_asset_dict(
                    asset_dict,
                    store=self._storage,
                    path_prefix=self._path_prefix,
                    path_key=f"{uuid.uuid4()}.{ext}",
                )

        def _make_handler_adapter(wrapped: _WrappedTaskHandler) -> Any:
            # HandlerRegistry.execute() invokes `await handler(*task.args, **task.kwargs)` —
            # handlers receive unpacked kwargs, not a single params dict. Adapt back to
            # the existing `run(self, params: dict)` handler shape.
            async def _adapter(**kwargs: Any) -> Any:
                return await wrapped.run(kwargs)

            return _adapter

        _TASK_HANDLER_SPECS = [
            ("tts", "tts_generation", "tts/", "_task_handler"),
            ("music", "music_generation", "music/", "_task_handler"),
            ("video", "video_generation", "video/", "_task_handler"),
            ("image", "image_generation", "image/", "_task_handler"),
            (
                "video",
                "video_processing",
                "video/processed/",
                "_processing_task_handler",
            ),
            ("upscale", "upscale_generation", "upscale/", "_task_handler"),
            (
                "interpolate",
                "interpolate_generation",
                "interpolate/",
                "_task_handler",
            ),
        ]
        for sub_key, task_name, segment, handler_attr in _TASK_HANDLER_SPECS:
            sub = self._sub_providers[sub_key]
            inner = getattr(sub, handler_attr)
            wrapped = _WrappedTaskHandler(
                inner=inner,
                storage=self._storage,
                path_prefix=f"{self._config.storage_path_prefix}{segment}",
            )
            self._wrapped_task_handlers[task_name] = wrapped
            task_provider.register_handler(task_name, _make_handler_adapter(wrapped))

        from lexigram.multimedia.timeline import TimelineRenderTask

        video_sub = self._sub_providers["video"]
        self._timeline_task_handler = TimelineRenderTask(
            processor=video_sub._processing_backend
        )
        timeline_wrapped = _WrappedTaskHandler(
            inner=self._timeline_task_handler,
            storage=self._storage,
            path_prefix=(f"{self._config.storage_path_prefix}video/composed/"),
        )
        self._wrapped_task_handlers["timeline_render"] = timeline_wrapped
        task_provider.register_handler(
            "timeline_render", _make_handler_adapter(timeline_wrapped)
        )

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

        sub = self._sub_providers["tts"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="tts_generation",
            storage=self._storage,
            path_prefix=f"{self._config.storage_path_prefix}tts/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend if self._config.cache_results else None,
            event_bus=self._event_bus,
            media_type="tts",
        )

    @property
    def music(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["music"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="music_generation",
            storage=self._storage,
            path_prefix=f"{self._config.storage_path_prefix}music/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend if self._config.cache_results else None,
            event_bus=self._event_bus,
            media_type="music",
        )

    @property
    def video(self) -> VideoAccessor:
        from lexigram.multimedia.accessors import SubsystemAccessor, VideoAccessor

        sub = self._sub_providers["video"]
        generation: SubsystemAccessor[Any] = SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="video_generation",
            storage=self._storage,
            path_prefix=f"{self._config.storage_path_prefix}video/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend if self._config.cache_results else None,
            event_bus=self._event_bus,
            media_type="video",
        )
        processing: SubsystemAccessor[Any] = SubsystemAccessor(
            backend=sub._processing_backend,
            task_manager=self._task_manager,
            task_name="video_processing",
            storage=self._storage,
            path_prefix=f"{self._config.storage_path_prefix}video/processed/",
            idempotency_manager=self._idempotency_manager,
            backend_method="process",
        )
        return VideoAccessor(
            generation=generation,
            processing=processing,
            storage=self._storage,
            path_prefix=(f"{self._config.storage_path_prefix}video/processed/in/"),
            video_upscale_service=self._sub_providers["upscale"]._video_upscale_service,
            video_interpolation_service=(
                self._sub_providers["interpolate"]._video_interpolation_service
            ),
        )

    @property
    def compose(self) -> ComposeAccessor:
        from lexigram.multimedia.accessors import ComposeAccessor

        sub = self._sub_providers["video"]
        return ComposeAccessor(
            processor=sub._processing_backend,
            task_manager=self._task_manager,
            task_name="timeline_render",
            storage=self._storage,
            path_prefix=(f"{self._config.storage_path_prefix}video/composed/in/"),
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
            path_prefix=f"{self._config.storage_path_prefix}image/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend if self._config.cache_results else None,
            event_bus=self._event_bus,
            media_type="image",
        )

    @property
    def upscale(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["upscale"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="upscale_generation",
            storage=self._storage,
            path_prefix=f"{self._config.storage_path_prefix}upscale/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend if self._config.cache_results else None,
            event_bus=self._event_bus,
            media_type="upscale",
            backend_method="upscale",
        )

    @property
    def interpolate(self) -> Any:
        from lexigram.multimedia.accessors import SubsystemAccessor

        sub = self._sub_providers["interpolate"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="interpolate_generation",
            storage=self._storage,
            path_prefix=f"{self._config.storage_path_prefix}interpolate/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend if self._config.cache_results else None,
            event_bus=self._event_bus,
            media_type="interpolate",
            backend_method="interpolate",
        )

    @property
    def beat(self) -> BeatAccessor:
        from lexigram.multimedia.accessors import BeatAccessor

        sub = self._sub_providers["beat"]
        return BeatAccessor(backend=sub._backend)
