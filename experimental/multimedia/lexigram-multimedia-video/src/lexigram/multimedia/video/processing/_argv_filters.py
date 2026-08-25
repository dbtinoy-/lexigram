"""ffmpeg argv builders for the visual filter operation family.

Covers ColorFilter, OverlayText, OverlayImage, BurnSubtitles, and
RawFilter. Pure functions: no subprocess execution or filesystem I/O.
"""

from __future__ import annotations

from lexigram.contracts.multimedia.types import (
    ColorFilter,
    OverlayImage,
    OverlayText,
    RawFilter,
)
from lexigram.multimedia.video.processing._argv_shared import (
    RE_COLOR,
    assert_filter_field,
    escape_drawtext,
)

__all__ = [
    "build_burn_subtitles_argv",
    "build_color_filter_argv",
    "build_overlay_image_argv",
    "build_overlay_text_argv",
    "build_raw_filter_argv",
]

_COLOR_PRESETS = {
    "grayscale": "hue=s=0",
    "sepia": (
        "colorchannelmixer=0.393:0.769:0.189:0:0.349:0.686:0.168:0:0.272:0.534:0.131"
    ),
    "vintage": "curves=vintage,vignette",
}

_POSITION_EXPR = {
    "top": "(w-text_w)/2:20",
    "bottom": "(w-text_w)/2:h-text_h-20",
    "center": "(w-text_w)/2:(h-text_h)/2",
    "top-left": "20:20",
    "top-right": "w-text_w-20:20",
    "bottom-left": "20:h-text_h-20",
    "bottom-right": "w-text_w-20:h-text_h-20",
}

_OVERLAY_POSITION_EXPR = {
    "top": "(W-w)/2:20",
    "bottom": "(W-w)/2:H-h-20",
    "center": "(W-w)/2:(H-h)/2",
    "top-left": "20:20",
    "top-right": "W-w-20:20",
    "bottom-left": "20:H-h-20",
    "bottom-right": "W-w-20:H-h-20",
}


def build_color_filter_argv(
    operation: ColorFilter,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`ColorFilter` operation."""
    if operation.preset and operation.preset != "none":
        vf = _COLOR_PRESETS[operation.preset]
    else:
        vf = (
            f"eq=brightness={operation.brightness}"
            f":contrast={operation.contrast}:saturation={operation.saturation}"
        )
    return [ffmpeg_binary, "-y", "-i", input_paths[0], "-vf", vf, output_path]


def build_overlay_text_argv(
    operation: OverlayText,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for an :class:`OverlayText` operation."""
    assert_filter_field("color", operation.color, RE_COLOR)
    if not 1 <= operation.font_size <= 512:
        raise ValueError(f"ffmpeg font_size out of range: {operation.font_size}")
    xy = _POSITION_EXPR[operation.position]
    drawtext = (
        f"drawtext=text='{escape_drawtext(operation.text)}'"
        f":fontsize={operation.font_size}"
        f":fontcolor={operation.color}:x={xy.split(':')[0]}:y={xy.split(':')[1]}"
    )
    if operation.start is not None and operation.end is not None:
        drawtext += f":enable='between(t,{operation.start},{operation.end})'"
    return [
        ffmpeg_binary,
        "-y",
        "-i",
        input_paths[0],
        "-vf",
        drawtext,
        output_path,
    ]


def build_overlay_image_argv(
    operation: OverlayImage,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for an :class:`OverlayImage` operation."""
    xy = _OVERLAY_POSITION_EXPR[operation.position]
    filters = []
    if operation.opacity < 1.0:
        filters.append(f"[1:v]colorchannelmixer=aa={operation.opacity}[ovl]")
        overlay_input = "[ovl]"
    else:
        overlay_input = "[1:v]"
    overlay_expr = f"[0:v]{overlay_input}overlay={xy}"
    if operation.start is not None and operation.end is not None:
        overlay_expr += f":enable='between(t,{operation.start},{operation.end})'"
    filters.append(overlay_expr + "[v]")
    return [
        ffmpeg_binary,
        "-y",
        "-i",
        input_paths[0],
        "-i",
        input_paths[1],
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[v]",
        "-map",
        "0:a?",
        output_path,
    ]


def build_burn_subtitles_argv(
    subtitle_path: str | None,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`BurnSubtitles` operation."""
    return [
        ffmpeg_binary,
        "-y",
        "-i",
        input_paths[0],
        "-vf",
        f"subtitles={subtitle_path}",
        output_path,
    ]


def build_raw_filter_argv(
    operation: RawFilter,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`RawFilter` operation."""
    argv = [ffmpeg_binary, "-y"]
    for path in input_paths:
        argv += ["-i", path]
    argv += ["-filter_complex", operation.filter_complex]
    for m in operation.maps:
        argv += ["-map", m]
    argv += operation.extra_args
    argv.append(output_path)
    return argv
