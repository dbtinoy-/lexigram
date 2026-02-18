"""Multimedia umbrella constants — shared defaults and core subsystem names."""

from __future__ import annotations

# Core multimedia subsystems discovered via entry points, in canonical order.
CORE_SUBSYSTEMS: tuple[str, ...] = (
    "tts",
    "music",
    "video",
    "image",
    "upscale",
    "interpolate",
    "beat",
)

__all__ = ["CORE_SUBSYSTEMS"]
