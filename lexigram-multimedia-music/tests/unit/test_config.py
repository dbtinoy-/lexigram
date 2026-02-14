from lexigram.multimedia.music.config import MusicConfig


def test_default_backend_is_local_http() -> None:
    cfg = MusicConfig()
    assert cfg.backend == "local-http"
    assert cfg.local_http_base_url == "http://localhost:5003"


def test_duration_seconds_defaults_to_30() -> None:
    cfg = MusicConfig()
    assert cfg.duration_seconds == 30.0


def test_new_backends_have_working_defaults() -> None:
    cfg = MusicConfig()
    assert cfg.ace_step_base_url == "http://localhost:5300"
    assert cfg.stable_audio_open_base_url == "http://localhost:5301"


def test_backend_literal_accepts_new_engines() -> None:
    for backend in ("ace-step", "stable-audio-open"):
        cfg = MusicConfig(backend=backend)  # type: ignore[arg-type]
        assert cfg.backend == backend
