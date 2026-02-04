"""Composes an InterpolationProvider with a VideoProcessor to double or
quadruple a whole video's frame rate.

Depends on both dependencies purely through lexigram-contracts protocols
and constructor injection — never a direct import of
lexigram-multimedia-video (design spec §4.3).
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.contracts.multimedia.types import InterpolationRequest, MediaAsset

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import (
        InterpolationProvider,
        VideoProcessor,
    )


class VideoInterpolationService:
    """Extracts a video's frames, doubles the sequence one or two passes,
    then reassembles at the resulting higher frame rate.

    Not itself an InterpolationProvider — a different method name
    (`interpolate_video`, not `interpolate`) and a different signature (a
    whole-video MediaAsset plus factor/fps, not a two-frame
    InterpolationRequest), mirroring how VideoUpscaleService in the
    Upscale design is deliberately not an UpscaleProvider either
    (design spec §6.2).
    """

    def __init__(
        self,
        interpolation_provider: InterpolationProvider,
        video_processor: VideoProcessor,
    ) -> None:
        self._interpolation_provider = interpolation_provider
        self._video_processor = video_processor

    async def interpolate_video(
        self, asset: MediaAsset, *, factor: Literal[2, 4] = 2, fps: float
    ) -> Result[MediaAsset, MultimediaError]:
        frames_result = await self._video_processor.extract_frames(asset)
        if frames_result.is_err():
            return Err(frames_result.unwrap_err())
        sequence = frames_result.unwrap()

        if not sequence:
            return Err(MultimediaError("extract_frames returned an empty frame list"))

        doublings = 1 if factor == 2 else 2
        for _ in range(doublings):
            doubled_result = await self._double(sequence)
            if doubled_result.is_err():
                return Err(doubled_result.unwrap_err())
            sequence = doubled_result.unwrap()

        assembled = await self._video_processor.assemble_frames(
            sequence, fps=fps * factor
        )
        return (
            Err(assembled.unwrap_err())
            if assembled.is_err()
            else Ok(assembled.unwrap())
        )

    async def _double(
        self, frames: list[MediaAsset]
    ) -> Result[list[MediaAsset], MultimediaError]:
        # Interleaves an interpolated midpoint frame between every
        # consecutive pair: [f0, f1, f2] -> [f0, mid01, f1, mid12, f2].
        doubled = [frames[0]]
        for a, b in pairwise(frames):
            mid_result = await self._interpolation_provider.interpolate(
                InterpolationRequest(frame_a=a, frame_b=b)
            )
            if mid_result.is_err():
                return Err(mid_result.unwrap_err())
            doubled += [mid_result.unwrap(), b]
        return Ok(doubled)


__all__ = ["VideoInterpolationService"]
