"""FFmpeg-backed VideoProcessor implementation."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    Concat,
    MediaAsset,
    MuxAudio,
    OverlayImage,
    VideoOperation,
)
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.exceptions import VideoProcessingError
from lexigram.multimedia.video.processing.argv import build_argv, cues_to_srt
from lexigram.multimedia.video.processing.media_io import (
    materialize_asset,
    probe_duration,
    read_output_asset,
)


class FFmpegVideoProcessor:
    """Runs ffmpeg subprocesses to fulfill VideoOperation requests."""

    def __init__(self, config: VideoProcessingConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent_jobs)

    async def process(
        self, operation: VideoOperation
    ) -> Result[MediaAsset, VideoProcessingError]:
        async with self._semaphore:
            workdir = tempfile.mkdtemp(dir=self._config.temp_dir)
            try:
                return await self._process(operation, workdir=workdir)
            except (OSError, ValueError) as exc:
                return Err(
                    VideoProcessingError(f"ffmpeg processing failed: {exc}", cause=exc)
                )
            finally:
                shutil.rmtree(workdir, ignore_errors=True)

    async def _process(
        self, operation: VideoOperation, *, workdir: str
    ) -> Result[MediaAsset, VideoProcessingError]:
        input_paths = await self._materialize_inputs(operation, workdir=workdir)
        output_path = f"{workdir}/{os.urandom(8).hex()}{self._output_suffix(operation)}"

        extra_kwargs: dict = {}
        if (
            isinstance(operation, Concat)
            and operation.transitions
            and any(t.kind == "crossfade" for t in operation.transitions)
        ):
            extra_kwargs["clip_durations"] = [
                await probe_duration(p, ffprobe_binary=self._ffprobe_binary())
                for p in input_paths
            ]
        if isinstance(operation, BurnSubtitles):
            subtitle_path = f"{workdir}/{os.urandom(8).hex()}.srt"
            with open(subtitle_path, "w") as f:
                f.write(cues_to_srt(operation.cues))
            extra_kwargs["subtitle_path"] = subtitle_path

        argv = build_argv(
            operation,
            input_paths=input_paths,
            output_path=output_path,
            ffmpeg_binary=self._config.ffmpeg_binary,
            **extra_kwargs,
        )

        result = await self._run(argv)
        if result.is_err():
            return Err(result.unwrap_err())

        # Read bytes into memory now — the workdir (including this output
        # file) is removed by process()'s finally block once we return.
        asset = read_output_asset(
            output_path,
            mime_type=self._output_mime_type(operation),
            provider="ffmpeg",
        )
        return Ok(asset)

    async def _materialize_inputs(
        self, operation: VideoOperation, *, workdir: str
    ) -> list[str]:
        match operation:
            case Concat(assets=assets):
                return [await materialize_asset(a, temp_dir=workdir) for a in assets]
            case OverlayImage(asset=asset, image_asset=image_asset):
                return [
                    await materialize_asset(asset, temp_dir=workdir),
                    await materialize_asset(image_asset, temp_dir=workdir),
                ]
            case MuxAudio(asset=asset, audio_asset=audio_asset):
                return [
                    await materialize_asset(asset, temp_dir=workdir),
                    await materialize_asset(audio_asset, temp_dir=workdir),
                ]
            case _:
                primary = getattr(operation, "asset", None)
                if primary is not None:
                    return [await materialize_asset(primary, temp_dir=workdir)]
                # RawFilter carries a list of assets directly.
                return [
                    await materialize_asset(a, temp_dir=workdir)
                    for a in operation.assets  # type: ignore[union-attr]
                ]

    async def _run(self, argv: list[str]) -> Result[None, VideoProcessingError]:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._config.timeout
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return Err(
                VideoProcessingError(f"ffmpeg timed out after {self._config.timeout}s")
            )

        if proc.returncode != 0:
            return Err(
                VideoProcessingError(f"ffmpeg error: {stderr.decode(errors='replace')}")
            )
        return Ok(None)

    def _ffprobe_binary(self) -> str:
        # ffprobe ships alongside ffmpeg; derive its name from the configured binary.
        if self._config.ffmpeg_binary.endswith("ffmpeg"):
            return self._config.ffmpeg_binary[: -len("ffmpeg")] + "ffprobe"
        return "ffprobe"

    def _output_suffix(self, operation: VideoOperation) -> str:
        from lexigram.contracts.multimedia.types import (
            ExtractThumbnail,
            ToGif,
            Transcode,
        )

        if isinstance(operation, ExtractThumbnail):
            return ".png"
        if isinstance(operation, ToGif):
            return ".gif"
        if isinstance(operation, Transcode):
            return f".{operation.format}"
        return ".mp4"

    def _output_mime_type(self, operation: VideoOperation) -> str:
        from lexigram.contracts.multimedia.types import (
            ExtractThumbnail,
            ToGif,
            Transcode,
        )

        if isinstance(operation, ExtractThumbnail):
            return "image/png"
        if isinstance(operation, ToGif):
            return "image/gif"
        if isinstance(operation, Transcode):
            return f"video/{operation.format}"
        return "video/mp4"


__all__ = ["FFmpegVideoProcessor"]
