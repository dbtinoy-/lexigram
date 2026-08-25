"""Pure ffmpeg argv builders — one function per VideoOperation variant.

No subprocess execution or filesystem I/O here; these functions only
assemble command-line argument lists so they're trivially unit-testable.

Builders are grouped by operation family in sibling modules:

* :mod:`._argv_timeline` — Trim, Crop, ChangeSpeed, Transcode,
  ExtractThumbnail, ToGif, MuxAudio, Concat.
* :mod:`._argv_filters` — ColorFilter, OverlayText, OverlayImage,
  BurnSubtitles, RawFilter.
* :mod:`._argv_compose` — ComposeVideo layered composition.
* :mod:`._argv_shared` — validation and escaping helpers.

This module keeps the public dispatch surface (:func:`build_argv`,
:func:`build_compose_argv`, :func:`cues_to_srt`).
"""

from __future__ import annotations

from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    ChangeSpeed,
    ColorFilter,
    Concat,
    Crop,
    ExtractThumbnail,
    MuxAudio,
    OverlayImage,
    OverlayText,
    RawFilter,
    ToGif,
    Transcode,
    Trim,
    VideoOperation,
)
from lexigram.multimedia.video.processing._argv_compose import build_compose_argv
from lexigram.multimedia.video.processing._argv_filters import (
    build_burn_subtitles_argv,
    build_color_filter_argv,
    build_overlay_image_argv,
    build_overlay_text_argv,
    build_raw_filter_argv,
)
from lexigram.multimedia.video.processing._argv_timeline import (
    build_change_speed_argv,
    build_concat_argv,
    build_crop_argv,
    build_mux_audio_argv,
    build_thumbnail_argv,
    build_to_gif_argv,
    build_transcode_argv,
    build_trim_argv,
)

__all__ = ["build_argv", "build_compose_argv", "cues_to_srt"]


def build_argv(
    operation: VideoOperation,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str = "ffmpeg",
    clip_durations: list[float] | None = None,
    subtitle_path: str | None = None,
) -> list[str]:
    """Dispatch an operation variant to its family's argv builder."""
    match operation:
        case Trim():
            return build_trim_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case Crop():
            return build_crop_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case ChangeSpeed():
            return build_change_speed_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case ColorFilter():
            return build_color_filter_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case Transcode():
            return build_transcode_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case ExtractThumbnail():
            return build_thumbnail_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case ToGif():
            return build_to_gif_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case OverlayText():
            return build_overlay_text_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case OverlayImage():
            return build_overlay_image_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case BurnSubtitles():
            return build_burn_subtitles_argv(
                subtitle_path,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case MuxAudio():
            return build_mux_audio_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
        case Concat():
            return build_concat_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
                clip_durations=clip_durations,
            )
        case RawFilter():
            return build_raw_filter_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
            )
    raise TypeError(f"unsupported operation: {operation!r}")


def cues_to_srt(cues: list) -> str:
    """Format transcript cues as an SRT subtitle document."""

    def fmt(t: float) -> str:
        hours, rem = divmod(t, 3600)
        minutes, seconds = divmod(rem, 60)
        millis = round((seconds - int(seconds)) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{millis:03d}"

    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{fmt(cue.start)} --> {fmt(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)
