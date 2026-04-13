from lexigram.multimedia.video.config import VideoConfig, VideoProcessingConfig


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


def test_video_processing_config_defaults() -> None:
    cfg = VideoProcessingConfig()
    assert cfg.ffmpeg_binary == "ffmpeg"
    assert cfg.max_concurrent_jobs == 2
    assert cfg.temp_dir is None
    assert cfg.timeout == 300.0


def test_video_config_has_processing_field() -> None:
    cfg = VideoConfig()
    assert isinstance(cfg.processing, VideoProcessingConfig)
