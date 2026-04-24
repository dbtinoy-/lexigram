from lexigram.multimedia.interpolate.config import InterpolationConfig


def test_interpolation_config_defaults() -> None:
    config = InterpolationConfig()
    assert config.backend == "rife"
    assert config.default_factor == 2
    assert config.timeout == 15.0
