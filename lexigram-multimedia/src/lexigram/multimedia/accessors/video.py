"""Video subsystem accessor — exposes generation and processing under `multimedia.video`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

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
        video_upscale_service: Any | None = None,
        video_interpolation_service: Any | None = None,
    ) -> None:
        self._generation = generation
        self._processing = processing
        self._storage = storage
        self._path_prefix = path_prefix
        self._video_upscale_service = video_upscale_service
        self._video_interpolation_service = video_interpolation_service

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

    async def upscale_video(
        self, asset: MediaAsset, *, scale_factor: Literal[2, 4] = 4
    ) -> Result[MediaAsset, MultimediaError]:
        """
        Upscale a whole video by a factor of 2 or 4.

        Requires a whole-video upscaling service, which is only built when a
        ``VideoProcessor`` was configured in the upscale subsystem.

        Args:
            asset: Source video asset to upscale.
            scale_factor: Upscale multiplier, 2 or 4. Defaults to 4.

        Returns:
            Ok(upscaled_asset) on success, Err(ProviderNotInstalledError) if no
            VideoProcessor was configured.

        Example:
            ```python
            result = await video.upscale_video(asset, scale_factor=2)
            if result.is_ok():
                print(result.unwrap().url)
            ```
        """
        from lexigram.contracts.core.result import Err
        from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

        if self._video_upscale_service is None:
            return Err(
                ProviderNotInstalledError(
                    "Whole-video upscaling requires a VideoProcessor to be "
                    "configured — none was found when the upscale subsystem "
                    "registered."
                )
            )
        upscaled: Result[MediaAsset, MultimediaError] = (
            await self._video_upscale_service.upscale_video(
                asset, scale_factor=scale_factor
            )
        )
        return upscaled

    async def interpolate_video(
        self, asset: MediaAsset, *, factor: Literal[2, 4] = 2, fps: float
    ) -> Result[MediaAsset, MultimediaError]:
        """
        Interpolate a whole video to a higher frame rate (motion smoothing).

        Requires a whole-video interpolation service, which is only built when
        a ``VideoProcessor`` was configured in the interpolate subsystem.

        Args:
            asset: Source video asset to interpolate.
            factor: Frame multiplier, 2 or 4. Defaults to 2.
            fps: Output target frame rate in frames per second.

        Returns:
            Ok(interpolated_asset) on success, Err(ProviderNotInstalledError) if
            no VideoProcessor was configured.

        Example:
            ```python
            result = await video.interpolate_video(asset, factor=2, fps=60.0)
            if result.is_ok():
                print(result.unwrap().url)
            ```
        """
        from lexigram.contracts.core.result import Err
        from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

        if self._video_interpolation_service is None:
            return Err(
                ProviderNotInstalledError(
                    "Whole-video interpolation requires a VideoProcessor to be "
                    "configured — none was found when the interpolate "
                    "subsystem registered."
                )
            )
        interpolated: Result[MediaAsset, MultimediaError] = (
            await self._video_interpolation_service.interpolate_video(
                asset, factor=factor, fps=fps
            )
        )
        return interpolated


__all__ = ["VideoAccessor"]
