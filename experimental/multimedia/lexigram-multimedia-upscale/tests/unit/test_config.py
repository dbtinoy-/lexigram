from lexigram.config import BaseConfig
from lexigram.multimedia.upscale.config import UpscaleConfig


def test_upscale_config_is_base_config() -> None:
    assert issubclass(UpscaleConfig, BaseConfig)
    assert UpscaleConfig.config_section == "multimedia_upscale"


def test_upscale_config_has_no_default_scale_factor() -> None:
    assert not hasattr(UpscaleConfig(), "default_scale_factor")


def test_upscale_config_from_dict() -> None:
    cfg = UpscaleConfig.from_dict({"backend": "hat", "timeout": 5.0})
    assert cfg.backend == "hat"
    assert cfg.timeout == 5.0


def test_upscale_config_defaults() -> None:
    config = UpscaleConfig()
    assert config.backend == "real-esrgan"
    assert config.timeout == 30.0