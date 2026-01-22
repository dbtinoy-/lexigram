"""Compose accessor — exposes timeline rendering, sync and queued, under `multimedia.compose`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.multimedia.exceptions import VideoGenerationError
    from lexigram.contracts.multimedia.types import MediaAsset
    from lexigram.multimedia.timeline import Timeline
    from lexigram.multimedia.types import JobHandle


class ComposeAccessor:
    """Exposes timeline rendering — sync and queued — under `multimedia.compose`."""

    def __init__(
        self,
        *,
        processor: Any,
        task_manager: Any,
        task_name: str,
        storage: Any,
        path_prefix: str,
        idempotency_manager: Any = None,
    ) -> None:
        self._processor = processor
        self._task_manager = task_manager
        self._task_name = task_name
        self._storage = storage
        self._path_prefix = path_prefix
        self._idempotency_manager = idempotency_manager

    async def render(
        self, timeline: Timeline
    ) -> Result[MediaAsset, VideoGenerationError]:
        return await timeline.render(self._processor)

    async def submit_render(
        self, timeline: Timeline, idempotency_key: str | None = None
    ) -> JobHandle:
        from lexigram.multimedia.storage import normalize_timeline_assets
        from lexigram.multimedia.types import JobHandle

        normalized = await normalize_timeline_assets(
            timeline, storage=self._storage, path_prefix=self._path_prefix
        )
        params = normalized.to_params()

        is_duplicate = False
        if self._idempotency_manager is not None:
            key = self._idempotency_manager.generate_key(
                self._task_name, params, idempotency_key
            )
            is_duplicate = (
                await self._idempotency_manager.check_duplicate(key) is not None
            )

        result = await self._task_manager.submit_task(
            self._task_name, params, idempotency_key=idempotency_key
        )
        return JobHandle.from_idempotency_result(result, is_duplicate=is_duplicate)


__all__ = ["ComposeAccessor"]
