"""Configuration for the beat-analysis subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from lexigram.config import BaseConfig


@dataclass(init=False)
class BeatAnalysisConfig(BaseConfig):
    """Configuration for the beat-analysis subsystem."""

    config_section: ClassVar[str] = "multimedia_beat"
    backend: Literal["librosa", "madmom"] = "librosa"
    librosa_sample_rate: int = 22050
    max_asset_bytes: int = 25 * 1024 * 1024
    max_analyze_samples: int = 60_000_000
    madmom_base_url: str = "http://localhost:5600"
    timeout: float = 30.0


__all__ = ["BeatAnalysisConfig"]
