"""Umbrella DI provider — orchestrates the 4 core multimedia sub-providers."""

from __future__ import annotations

import importlib.metadata
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
    from lexigram.multimedia.compose_accessor import ComposeAccessor
    from lexigram.multimedia.timeline_task import TimelineRenderTask
    from lexigram.multimedia.video_accessor import VideoAccessor

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
        self._timeline_task_handler: TimelineRenderTask | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.multimedia.audio_music.di.provider import AudioMusicProvider
        from lexigram.multimedia.audio_tts.di.provider import AudioTTSProvider
        from lexigram.multimedia.image.di.provider import ImageGenerationProvider
        from lexigram.multimedia.video.di.provider import VideoGenerationProvider

        self._sub_providers["audio-tts"] = AudioTTSProvider(
            config=self._multimedia_config.tts
        )
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
            for _ep in importlib.metadata.entry_points(
                group="lexigram.multimedia.subsystems"
            ):
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

        from lexigram.contracts.events.protocols import EventBusProtocol

        try:
            self._event_bus = await container.resolve(EventBusProtocol)
        except (LookupError, KeyError, ValueError, TypeError):
            self._event_bus = None
            logger.debug("multimedia_no_event_bus_bound; generation events disabled")

        await self._wire_task_manager(container)

    async def _wire_task_manager(self, container: ContainerResolverProtocol) -> None:
        from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
        from lexigram.contracts.infra.tasks import TaskQueueProtocol
        from lexigram.multimedia.idempotency_store import (
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
        except (LookupError, KeyError, ValueError, TypeError):
            logger.warning(
                "multimedia_no_task_provider_bound",
                reason="lexigram-tasks not configured — submit() will be unavailable, "
                "only the synchronous generate() path will work",
            )
            return

        idempotency_store: Any
        try:
            idempotency_store = await container.resolve(IdempotencyStoreProtocol)
        except (LookupError, KeyError, ValueError, TypeError):
            idempotency_store = InMemoryIdempotencyStoreFallback()

        idempotency_manager = IdempotencyManager(storage=idempotency_store)
        self._idempotency_manager = idempotency_manager
        self._task_manager = IdempotentTaskManager(
            queue_client=task_queue, idempotency_manager=idempotency_manager
        )

        import uuid

        from lexigram.multimedia.storage_normalize import normalize_asset_dict

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
            ("audio-tts", "tts_generation", "tts/", "_task_handler"),
            ("audio-music", "music_generation", "music/", "_task_handler"),
            ("video", "video_generation", "video/", "_task_handler"),
            ("image", "image_generation", "image/", "_task_handler"),
            (
                "video",
                "video_processing",
                "video/processed/",
                "_processing_task_handler",
            ),
        ]
        for sub_key, task_name, segment, handler_attr in _TASK_HANDLER_SPECS:
            sub = self._sub_providers[sub_key]
            inner = getattr(sub, handler_attr)
            wrapped = _WrappedTaskHandler(
                inner=inner,
                storage=self._storage,
                path_prefix=f"{self._multimedia_config.storage_path_prefix}{segment}",
            )
            self._wrapped_task_handlers[task_name] = wrapped
            task_provider.register_handler(task_name, _make_handler_adapter(wrapped))

        from lexigram.multimedia.timeline_task import TimelineRenderTask

        video_sub = self._sub_providers["video"]
        self._timeline_task_handler = TimelineRenderTask(
            processor=video_sub._processing_backend
        )
        timeline_wrapped = _WrappedTaskHandler(
            inner=self._timeline_task_handler,
            storage=self._storage,
            path_prefix=(
                f"{self._multimedia_config.storage_path_prefix}video/composed/"
            ),
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

        sub = self._sub_providers["audio-tts"]
        return SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="tts_generation",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}tts/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend
            if self._multimedia_config.cache_results
            else None,
            event_bus=self._event_bus,
            media_type="tts",
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
            cache_backend=self._cache_backend
            if self._multimedia_config.cache_results
            else None,
            event_bus=self._event_bus,
            media_type="music",
        )

    @property
    def video(self) -> VideoAccessor:
        from lexigram.multimedia.accessors import SubsystemAccessor
        from lexigram.multimedia.video_accessor import VideoAccessor

        sub = self._sub_providers["video"]
        generation: SubsystemAccessor[Any] = SubsystemAccessor(
            backend=sub._backend,
            task_manager=self._task_manager,
            task_name="video_generation",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}video/",
            idempotency_manager=self._idempotency_manager,
            cache_backend=self._cache_backend
            if self._multimedia_config.cache_results
            else None,
            event_bus=self._event_bus,
            media_type="video",
        )
        processing: SubsystemAccessor[Any] = SubsystemAccessor(
            backend=sub._processing_backend,
            task_manager=self._task_manager,
            task_name="video_processing",
            storage=self._storage,
            path_prefix=f"{self._multimedia_config.storage_path_prefix}video/processed/",
            idempotency_manager=self._idempotency_manager,
            backend_method="process",
        )
        return VideoAccessor(
            generation=generation,
            processing=processing,
            storage=self._storage,
            path_prefix=(
                f"{self._multimedia_config.storage_path_prefix}video/processed/in/"
            ),
        )

    @property
    def compose(self) -> ComposeAccessor:
        from lexigram.multimedia.compose_accessor import ComposeAccessor

        sub = self._sub_providers["video"]
        return ComposeAccessor(
            processor=sub._processing_backend,
            task_manager=self._task_manager,
            task_name="timeline_render",
            storage=self._storage,
            path_prefix=(
                f"{self._multimedia_config.storage_path_prefix}video/composed/in/"
            ),
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
            cache_backend=self._cache_backend
            if self._multimedia_config.cache_results
            else None,
            event_bus=self._event_bus,
            media_type="image",
        )
