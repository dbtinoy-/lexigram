"""Beat-analysis provider backends."""

from __future__ import annotations

from lexigram.multimedia.beat.providers.librosa import LibrosaBeatAnalysisProvider
from lexigram.multimedia.beat.providers.madmom import MadmomBeatAnalysisProvider

__all__ = ["LibrosaBeatAnalysisProvider", "MadmomBeatAnalysisProvider"]
