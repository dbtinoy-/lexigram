from lexigram.multimedia.upscale.config import UpscaleConfig


def test_upscale_config_defaults() -> None:
    config = UpscaleConfig()
    assert config.backend == "real-esrgan"
    assert config.default_scale_factor == 4
    assert config.timeout == 30.0
