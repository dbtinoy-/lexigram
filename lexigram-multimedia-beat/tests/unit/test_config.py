from lexigram.multimedia.beat.config import BeatAnalysisConfig


def test_beat_analysis_config_defaults() -> None:
    config = BeatAnalysisConfig()
    assert config.backend == "librosa"
    assert config.librosa_sample_rate == 22050
    assert config.timeout == 30.0
