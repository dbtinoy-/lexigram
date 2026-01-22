"""Accessors exposing multimedia capabilities — sync and queued.

``SubsystemAccessor`` wraps one sub-provider's backend + task manager +
storage normalizer; ``VideoAccessor`` composes generation and processing
accessors for the video subsystem; ``ComposeAccessor`` exposes timeline
rendering — sync and queued — under ``multimedia.compose``.
"""

from lexigram.multimedia.accessors.compose import ComposeAccessor
from lexigram.multimedia.accessors.subsystem import SubsystemAccessor
from lexigram.multimedia.accessors.video import VideoAccessor

__all__ = ["ComposeAccessor", "SubsystemAccessor", "VideoAccessor"]
