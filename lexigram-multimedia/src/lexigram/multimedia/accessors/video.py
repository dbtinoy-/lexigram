"""Video subsystem accessor — exposes generation and processing under `multimedia.video`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.multimedia.exceptions import MultimediaError
    from lexigram.contracts.multimedia.types import (
        MediaAsset,
        VideoOperation,
        VideoRequest,
    )
    from lexigram.multimedia.accessors import SubsystemAccessor
    from lexigram.multimedia.types import JobHandle


class VideoAccessor:
    """Exposes both video generation and video processing under `multimedia.video`."""

    def __init__(
        self,
        *,
        generation: SubsystemAccessor,
        processing: SubsystemAccessor,
        storage: Any,
        path_prefix: str,
    ) -> None:
        self._generation = generation
        self._processing = processing
        self._storage = storage
        self._path_prefix = path_prefix

    async def generate(
        self, request: VideoRequest
    ) -> Result[MediaAsset, MultimediaError]:
        return await self._generation.generate(request)

    async def submit(
        self, request: VideoRequest, idempotency_key: str | None = None
    ) -> JobHandle:
        return await self._generation.submit(request, idempotency_key=idempotency_key)

    async def process(
        self, operation: VideoOperation
    ) -> Result[MediaAsset, MultimediaError]:
        return await self._processing.generate(operation)

    async def submit_process(
        self, operation: VideoOperation, idempotency_key: str | None = None
    ) -> JobHandle:
        import dataclasses

        from lexigram.multimedia.storage import normalize_operation_assets
        from lexigram.multimedia.types import JobHandle

        normalized = await normalize_operation_assets(
            operation, storage=self._storage, path_prefix=self._path_prefix
        )
        params = dataclasses.asdict(normalized)
        params["operation_type"] = type(normalized).__name__

        is_duplicate = False
        if self._processing._idempotency_manager is not None:
            key = self._processing._idempotency_manager.generate_key(
                self._processing._task_name, params, idempotency_key
            )
            is_duplicate = (
                await self._processing._idempotency_manager.check_duplicate(key)
                is not None
            )

        result = await self._processing._task_manager.submit_task(
            self._processing._task_name, params, idempotency_key=idempotency_key
        )
        return JobHandle.from_idempotency_result(result, is_duplicate=is_duplicate)


__all__ = ["VideoAccessor"]
