"""Lexigram Multimedia — generation umbrella package.

Install `lexigram-multimedia` to get the full multimedia subsystem.
Import from sub-packages for granular control.
"""

from __future__ import annotations

import pkgutil

# Critical: enable namespace-package discovery for lexigram.multimedia.*
# sibling distributions (tts, music, video, image).
__path__ = pkgutil.extend_path(__path__, __name__)

from lexigram.multimedia.accessors import (
    ComposeAccessor,
    SubsystemAccessor,
    VideoAccessor,
)
from lexigram.multimedia.config import MultimediaConfig
from lexigram.multimedia.di.provider import MultimediaProvider
from lexigram.multimedia.events import MultimediaGenerationEvent
from lexigram.multimedia.module import MultimediaModule
from lexigram.multimedia.timeline import Timeline, TimelineRenderTask
from lexigram.multimedia.types import JobHandle

__all__ = [
    "ComposeAccessor",
    "JobHandle",
    "MultimediaConfig",
    "MultimediaGenerationEvent",
    "MultimediaModule",
    "MultimediaProvider",
    "SubsystemAccessor",
    "Timeline",
    "TimelineRenderTask",
    "VideoAccessor",
]
