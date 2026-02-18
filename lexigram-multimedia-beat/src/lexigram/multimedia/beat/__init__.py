"""Audio tempo/beat analysis subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.beat.config import BeatAnalysisConfig
from lexigram.multimedia.beat.di import BeatAnalysisGenerationProvider
from lexigram.multimedia.beat.exceptions import (
    BeatAnalysisConnectionError,
    BeatAnalysisDecodeError,
    BeatAnalysisTimeoutError,
)
from lexigram.multimedia.beat.module import BeatAnalysisModule
from lexigram.multimedia.beat.providers import (
    LibrosaBeatAnalysisProvider,
    MadmomBeatAnalysisProvider,
)

__all__ = [
    "BeatAnalysisConfig",
    "BeatAnalysisConnectionError",
    "BeatAnalysisDecodeError",
    "BeatAnalysisGenerationProvider",
    "BeatAnalysisModule",
    "BeatAnalysisTimeoutError",
    "LibrosaBeatAnalysisProvider",
    "MadmomBeatAnalysisProvider",
]
