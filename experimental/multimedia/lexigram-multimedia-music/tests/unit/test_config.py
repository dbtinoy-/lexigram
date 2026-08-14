from lexigram.config import BaseConfig
from lexigram.multimedia.music.config import MusicConfig


def test_music_config_is_base_config() -> None:
    assert issubclass(MusicConfig, BaseConfig)
    assert MusicConfig.config_section == "multimedia_music"


def test_music_config_from_dict() -> None:
    cfg = MusicConfig.from_dict({"backend": "ace-step", "timeout": 5.0})
    assert cfg.backend == "ace-step"
    assert cfg.timeout == 5.0


def test_music_config_has_no_stability_fields() -> None:
    cfg = MusicConfig()
    assert not hasattr(cfg, "stability_api_key_secret_name")
    assert not hasattr(cfg, "duration_seconds")


def test_stability_audio_stays_a_valid_but_unimplemented_backend() -> None:
    cfg = MusicConfig.from_dict({"backend": "stability-audio"})
    assert cfg.backend == "stability-audio"


def test_default_backend_is_local_http() -> None:
    cfg = MusicConfig()
    assert cfg.backend == "local-http"
    assert cfg.local_http_base_url == "http://localhost:5003"


def test_new_backends_have_working_defaults() -> None:
    cfg = MusicConfig()
    assert cfg.ace_step_base_url == "http://localhost:5300"
    assert cfg.stable_audio_open_base_url == "http://localhost:5301"


def test_backend_literal_accepts_new_engines() -> None:
    for backend in ("ace-step", "stable-audio-open"):
        cfg = MusicConfig(backend=backend)  # type: ignore[arg-type]
        assert cfg.backend == backend
