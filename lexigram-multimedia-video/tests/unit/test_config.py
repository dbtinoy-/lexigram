from lexigram.multimedia.video.config import VideoConfig


def test_default_config_points_at_local_http() -> None:
    config = VideoConfig()
    assert config.backend == "local-http"
    assert config.local_http_base_url == "http://localhost:5004"
    assert config.runway_api_key_secret_name == "runway_api_key"
    assert config.timeout == 60.0


def test_runway_backend_configured_explicitly() -> None:
    config = VideoConfig(
        backend="runway",
        runway_api_key_secret_name="lex_my_runway_key",
    )
    assert config.backend == "runway"
    assert config.runway_api_key_secret_name == "lex_my_runway_key"
