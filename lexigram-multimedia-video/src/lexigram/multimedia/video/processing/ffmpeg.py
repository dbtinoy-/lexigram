"""FFmpeg-backed VideoProcessor implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import os
from pathlib import Path
import shutil
import tempfile

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    ComposeVideo,
    Concat,
    MediaAsset,
    MuxAudio,
    OverlayImage,
    VideoOperation,
)
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.exceptions import VideoProcessingError
from lexigram.multimedia.video.processing.argv import (
    build_argv,
    build_compose_argv,
    cues_to_srt,
)
from lexigram.multimedia.video.processing.media_io import (
    materialize_asset,
    materialize_frames_sequential,
    probe_duration,
    probe_fps,
    read_output_asset,
)


class FFmpegVideoProcessor:
    """Runs ffmpeg subprocesses to fulfill VideoOperation requests."""

    def __init__(self, config: VideoProcessingConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent_jobs)

    async def process(
        self,
        operation: VideoOperation,
        *,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Result[MediaAsset, VideoProcessingError]:
        async with self._semaphore:
            workdir = tempfile.mkdtemp(dir=self._config.temp_dir)
            try:
                if progress_callback is None:
                    return await self._process(operation, workdir=workdir)
                return await self._process_streaming(
                    operation, workdir=workdir, progress_callback=progress_callback
                )
            except (OSError, ValueError) as exc:
                return Err(
                    VideoProcessingError(f"ffmpeg processing failed: {exc}", cause=exc)
                )
            finally:
                shutil.rmtree(workdir, ignore_errors=True)

    async def extract_frames(
        self, asset: MediaAsset, *, fps: float | None = None
    ) -> Result[list[MediaAsset], VideoProcessingError]:
        async with self._semaphore:
            workdir = tempfile.mkdtemp(dir=self._config.temp_dir)
            try:
                input_path = await materialize_asset(asset, temp_dir=workdir)
                used_fps = fps
                if used_fps is None:
                    used_fps = await probe_fps(
                        input_path, ffprobe_binary=self._ffprobe_binary()
                    )
                framedir = f"{workdir}/frames"
                Path(framedir).mkdir()
                argv = [self._config.ffmpeg_binary, "-y", "-i", input_path]
                if fps is not None:
                    argv += ["-vf", f"fps={fps}"]
                argv += [f"{framedir}/frame%06d.png"]

                result = await self._run(argv)
                if result.is_err():
                    return Err(result.unwrap_err())

                frame_paths = sorted(str(p) for p in Path(framedir).glob("frame*.png"))
                frames = [
                    read_output_asset(p, mime_type="image/png", provider="ffmpeg")
                    for p in frame_paths
                ]
                frames = [
                    MediaAsset(
                        mime_type=f.mime_type,
                        provider=f.provider,
                        bytes_data=f.bytes_data,
                        metadata={"source_fps": used_fps},
                    )
                    for f in frames
                ]
                return Ok(frames)
            except (OSError, ValueError) as exc:
                return Err(
                    VideoProcessingError(
                        f"ffmpeg frame extraction failed: {exc}", cause=exc
                    )
                )
            finally:
                shutil.rmtree(workdir, ignore_errors=True)

    async def assemble_frames(
        self, frames: list[MediaAsset], *, fps: float
    ) -> Result[MediaAsset, VideoProcessingError]:
        async with self._semaphore:
            workdir = tempfile.mkdtemp(dir=self._config.temp_dir)
            try:
                pattern = materialize_frames_sequential(frames, temp_dir=workdir)
                output_path = f"{workdir}/{os.urandom(8).hex()}.mp4"
                argv = [
                    self._config.ffmpeg_binary,
                    "-y",
                    "-framerate",
                    str(fps),
                    "-i",
                    pattern,
                    "-pix_fmt",
                    "yuv420p",
                    output_path,
                ]

                result = await self._run(argv)
                if result.is_err():
                    return Err(result.unwrap_err())

                asset = read_output_asset(
                    output_path, mime_type="video/mp4", provider="ffmpeg"
                )
                return Ok(asset)
            except (OSError, ValueError) as exc:
                return Err(
                    VideoProcessingError(
                        f"ffmpeg frame assembly failed: {exc}", cause=exc
                    )
                )
            finally:
                shutil.rmtree(workdir, ignore_errors=True)

    async def _process(
        self, operation: VideoOperation, *, workdir: str
    ) -> Result[MediaAsset, VideoProcessingError]:
        _input_paths, output_path, argv = await self._prepare(
            operation, workdir=workdir
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

    async def _process_streaming(
        self,
        operation: VideoOperation,
        *,
        workdir: str,
        progress_callback: Callable[[float], None],
    ) -> Result[MediaAsset, VideoProcessingError]:
        input_paths, output_path, argv = await self._prepare(operation, workdir=workdir)

        duration_hint = await probe_duration(
            input_paths[0], ffprobe_binary=self._ffprobe_binary()
        )

        result = await self._run_streaming(
            argv,
            duration_hint=duration_hint,
            progress_callback=progress_callback,
        )
        if result.is_err():
            return Err(result.unwrap_err())

        asset = read_output_asset(
            output_path,
            mime_type=self._output_mime_type(operation),
            provider="ffmpeg",
        )
        return Ok(asset)

    async def _prepare(
        self, operation: VideoOperation, *, workdir: str
    ) -> tuple[list[str], str, list[str]]:
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
        if isinstance(operation, ComposeVideo):
            extra_kwargs["base_duration"] = await probe_duration(
                input_paths[0], ffprobe_binary=self._ffprobe_binary()
            )
            if any(
                layer.fade_out > 0 and layer.end is None for layer in operation.layers
            ):
                extra_kwargs["layer_durations"] = [
                    await probe_duration(p, ffprobe_binary=self._ffprobe_binary())
                    for p in input_paths[1 : 1 + len(operation.layers)]
                ]

        if isinstance(operation, ComposeVideo):
            argv = build_compose_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=self._config.ffmpeg_binary,
                **extra_kwargs,
            )
        else:
            argv = build_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=self._config.ffmpeg_binary,
                **extra_kwargs,
            )
        return input_paths, output_path, argv

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
            case ComposeVideo(asset=asset, layers=layers, audio_layers=audio_layers):
                return [
                    await materialize_asset(a, temp_dir=workdir)
                    for a in (
                        [asset]
                        + [layer.asset for layer in layers]
                        + [audio.asset for audio in audio_layers]
                    )
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

    async def _run_streaming(
        self,
        argv: list[str],
        *,
        duration_hint: float,
        progress_callback: Callable[[float], None],
    ) -> Result[None, VideoProcessingError]:
        stream_argv = argv[:]
        # Global ffmpeg options; position is irrelevant, but keeping them
        # right after the binary leaves the trailing output-path slot intact.
        stream_argv[1:1] = ["-nostats", "-progress", "pipe:1"]
        proc = await asyncio.create_subprocess_exec(
            *stream_argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        assert proc.stderr is not None
        stdout = proc.stdout
        stderr = proc.stderr

        stderr_chunks: list[bytes] = []

        async def _drain_stderr() -> None:
            while True:
                line = await stderr.readline()
                if not line:
                    break
                stderr_chunks.append(line)

        stderr_task = asyncio.create_task(_drain_stderr())

        async def _stream() -> int:
            last = 0.0
            while True:
                line = await stdout.readline()
                if not line:
                    break
                text = line.decode(errors="replace").strip()
                if not text.startswith("out_time"):
                    continue
                key, _, raw = text.partition("=")
                try:
                    value = float(raw)
                except ValueError:
                    continue
                seconds = (
                    value / 1000.0 if key == "out_time_ms" else value / 1_000_000.0
                )
                pct = min(1.0, seconds / duration_hint)
                if pct >= last + 0.01 or pct == 1.0:
                    progress_callback(pct)
                    last = pct
            await proc.wait()
            return proc.returncode or 0

        try:
            returncode = await asyncio.wait_for(_stream(), timeout=self._config.timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            stderr_task.cancel()
            return Err(
                VideoProcessingError(f"ffmpeg timed out after {self._config.timeout}s")
            )

        await stderr_task
        stderr_data = b"".join(stderr_chunks)
        if returncode != 0:
            return Err(
                VideoProcessingError(
                    f"ffmpeg error: {stderr_data.decode(errors='replace')}"
                )
            )
        progress_callback(1.0)
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
