"""Shared validation and escaping helpers for ffmpeg argv builders."""

from __future__ import annotations

import re

__all__ = ["assert_filter_field", "escape_drawtext"]

RE_COLOR = re.compile(r"^[a-zA-Z0-9_#]{1,32}$")  # ffmpeg named colors/0xRRGGBB
RE_CODEC = re.compile(r"^[a-zA-Z0-9_\-]{1,32}$")  # narrowed by ALLOWED_CODECS
RE_RESOLUTION = re.compile(r"^\d{1,5}x\d{1,5}$")
RE_BITRATE = re.compile(r"^\d{1,9}[kKmMgG]?$")
ALLOWED_CODECS = frozenset(
    {"libx264", "h264", "libx265", "h265", "libvpx-vp9", "vp9", "aac", "mp3", "copy"}
)


def assert_filter_field(
    kind: str,
    value: str,
    regex: re.Pattern[str],
    *,
    allowed: frozenset[str] | None = None,
) -> None:
    """Validate an interpolated filter field against its allow-list/regex."""
    if allowed is not None and value not in allowed:
        raise ValueError(f"unsupported ffmpeg {kind}: {value!r}")
    if not regex.match(value):
        raise ValueError(f"unsafe ffmpeg {kind} value: {value!r}")


def escape_drawtext(text: str) -> str:
    """Escape text for safe interpolation into a ``drawtext`` filter."""
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
