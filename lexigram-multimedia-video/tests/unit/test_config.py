from lexigram.config import BaseConfig
from lexigram.multimedia.video.config import VideoConfig, VideoProcessingConfig


def test_video_config_is_base_config() -> None:
    assert issubclass(VideoConfig, BaseConfig)
    assert VideoConfig.config_section == "multimedia_video"


def test_video_config_from_dict_with_nested_processing() -> None:
    cfg = VideoConfig.from_dict(
        {"backend": "runway", "processing": {"ffmpeg_binary": "ffmpeg42"}}
    )
    assert cfg.backend == "runway"
    assert cfg.processing.ffmpeg_binary == "ffmpeg42"


def test_default_config_points_at_local_http() -> None:
    config = VideoConfig()
    assert config.backend == "local-http"
    assert config.local_http_base_url == "http://localhost:5004"
    assert config.runway_api_key_secret_name == "runway_api_key"
    assert config.timeout is None


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


def test_new_backends_have_working_defaults() -> None:
    cfg = VideoConfig()
    assert cfg.openai_model == "sora-2"
    assert cfg.openai_base_url == "https://api.openai.com"
    assert cfg.wan22_base_url == "http://localhost:5200"
    assert cfg.cogvideox_base_url == "http://localhost:5201"
    assert cfg.svd_base_url == "http://localhost:5202"
    assert cfg.comfyui_base_url == "http://localhost:8188"
    assert cfg.comfyui_checkpoint == "svd_xt_1_1.safetensors"
    assert cfg.comfyui_workflow_path is None
    assert cfg.comfyui_fps == 6
    assert cfg.comfyui_motion_bucket_id == 127
    assert cfg.comfyui_poll_interval == 1.0


def test_backend_literal_accepts_all_new_engines() -> None:
    for backend in ("openai", "wan22", "cogvideox", "svd", "comfyui"):
        cfg = VideoConfig(backend=backend)  # type: ignore[arg-type]
        assert cfg.backend == backend
