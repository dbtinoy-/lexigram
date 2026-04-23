"""Composes an UpscaleProvider with a VideoProcessor to upscale whole videos.

Depends on both dependencies purely through lexigram-contracts protocols
and constructor injection — never a direct import of
lexigram-multimedia-video (design spec §4.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from lexigram.contracts.core.result import Err, Result
from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.contracts.multimedia.types import MediaAsset, UpscaleRequest

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import UpscaleProvider, VideoProcessor

_DEFAULT_FPS = 30.0


class VideoUpscaleService:
    """Extracts a video's frames, upscales each, then reassembles them.

    Not itself an UpscaleProvider — a different method name
    (`upscale_video`, not `upscale`) and a different signature (a
    whole-video MediaAsset plus scale_factor, not an UpscaleRequest),
    since video upscaling isn't a drop-in single-frame operation
    (design spec §6.3).
    """

    def __init__(
        self, upscale_provider: UpscaleProvider, video_processor: VideoProcessor
    ) -> None:
        self._upscale_provider = upscale_provider
        self._video_processor = video_processor

    async def upscale_video(
        self, asset: MediaAsset, *, scale_factor: Literal[2, 4] = 4
    ) -> Result[MediaAsset, MultimediaError]:
        frames_result = await self._video_processor.extract_frames(asset)
        if frames_result.is_err():
            return Err(frames_result.unwrap_err())
        frames = frames_result.unwrap()

        upscaled_frames: list[MediaAsset] = []
        for frame in frames:
            result = await self._upscale_provider.upscale(
                UpscaleRequest(asset=frame, scale_factor=scale_factor)
            )
            if result.is_err():
                return Err(result.unwrap_err())
            upscaled_frames.append(result.unwrap())

        source_fps = (
            frames[0].metadata.get("source_fps", _DEFAULT_FPS)
            if frames
            else _DEFAULT_FPS
        )
        return await self._video_processor.assemble_frames(
            upscaled_frames, fps=source_fps
        )


__all__ = ["VideoUpscaleService"]
