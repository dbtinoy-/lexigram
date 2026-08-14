from lexigram.config import BaseConfig
from lexigram.multimedia.image.config import ImageConfig


def test_image_config_is_base_config() -> None:
    assert issubclass(ImageConfig, BaseConfig)
    assert ImageConfig.config_section == "multimedia_image"


def test_image_config_from_dict_and_redaction() -> None:
    cfg = ImageConfig.from_dict(
        {"backend": "openai", "stability_api_key_secret_name": "lex_stability"}
    )
    assert cfg.backend == "openai"
    assert cfg.to_safe_dict()["stability_api_key_secret_name"] == "***"


def test_default_config_points_at_local_http() -> None:
    config = ImageConfig()
    assert config.backend == "local-http"
    assert config.local_http_base_url == "http://localhost:5005"
    assert config.stability_api_key_secret_name == "stability_api_key"
    assert config.timeout == 60.0


def test_stability_backend_configured_explicitly() -> None:
    config = ImageConfig(
        backend="stability",
        stability_api_key_secret_name="lex_my_stability_key",
    )
    assert config.backend == "stability"
    assert config.stability_api_key_secret_name == "lex_my_stability_key"


def test_new_backends_have_working_defaults() -> None:
    cfg = ImageConfig()
    assert cfg.openai_model == "dall-e-3"
    assert cfg.openai_base_url == "https://api.openai.com"
    assert cfg.comfyui_base_url == "http://localhost:8188"
    assert cfg.comfyui_checkpoint == "sd_xl_base_1.0.safetensors"
    assert cfg.comfyui_workflow_path is None
    assert cfg.comfyui_steps == 20
    assert cfg.comfyui_cfg_scale == 7.0
    assert cfg.comfyui_poll_interval == 1.0


def test_backend_literal_accepts_new_engines() -> None:
    for backend in ("openai", "comfyui"):
        cfg = ImageConfig(backend=backend)  # type: ignore[arg-type]
        assert cfg.backend == backend
