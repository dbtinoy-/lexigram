from lexigram.multimedia.image.config import ImageConfig


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
