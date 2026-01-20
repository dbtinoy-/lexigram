"""FFmpeg-based video processing: processor and media I/O helpers."""

from __future__ import annotations

from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor
from lexigram.multimedia.video.processing.media_io import (
    materialize_asset,
    probe_duration,
    read_output_asset,
)

__all__ = [
    "FFmpegVideoProcessor",
    "materialize_asset",
    "probe_duration",
    "read_output_asset",
]
