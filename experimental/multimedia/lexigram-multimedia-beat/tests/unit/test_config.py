from lexigram.config import BaseConfig
from lexigram.multimedia.beat.config import BeatAnalysisConfig


def test_beat_config_is_base_config() -> None:
    assert issubclass(BeatAnalysisConfig, BaseConfig)
    assert BeatAnalysisConfig.config_section == "multimedia_beat"


def test_beat_config_from_dict() -> None:
    cfg = BeatAnalysisConfig.from_dict({"backend": "madmom"})
    assert cfg.backend == "madmom"


def test_beat_analysis_config_defaults() -> None:
    config = BeatAnalysisConfig()
    assert config.backend == "librosa"
    assert config.librosa_sample_rate == 22050
    assert config.timeout == 30.0
