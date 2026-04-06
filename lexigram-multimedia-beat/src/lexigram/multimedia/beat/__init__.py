"""Audio tempo/beat analysis subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.beat.config import BeatAnalysisConfig
from lexigram.multimedia.beat.di import BeatAnalysisGenerationProvider
from lexigram.multimedia.beat.exceptions import BeatAnalysisDecodeError
from lexigram.multimedia.beat.module import BeatAnalysisModule
from lexigram.multimedia.beat.providers import (
    LibrosaBeatAnalysisProvider,
    MadmomBeatAnalysisProvider,
)

__all__ = [
    "BeatAnalysisConfig",
    "BeatAnalysisDecodeError",
    "BeatAnalysisGenerationProvider",
    "BeatAnalysisModule",
    "LibrosaBeatAnalysisProvider",
    "MadmomBeatAnalysisProvider",
]
