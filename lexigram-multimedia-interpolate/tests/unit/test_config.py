from lexigram.config import BaseConfig
from lexigram.multimedia.interpolate.config import InterpolationConfig


def test_interpolation_config_is_base_config() -> None:
    assert issubclass(InterpolationConfig, BaseConfig)
    assert InterpolationConfig.config_section == "multimedia_interpolate"


def test_interpolation_config_has_no_default_factor() -> None:
    assert not hasattr(InterpolationConfig(), "default_factor")


def test_interpolation_config_from_dict() -> None:
    cfg = InterpolationConfig.from_dict({"timeout": 3.0})
    assert cfg.timeout == 3.0


def test_interpolation_config_defaults() -> None:
    config = InterpolationConfig()
    assert config.backend == "rife"
    assert config.timeout == 15.0