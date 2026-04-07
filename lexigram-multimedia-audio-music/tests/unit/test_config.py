from lexigram.multimedia.audio_music.config import MusicConfig


def test_default_backend_is_local_http() -> None:
    cfg = MusicConfig()
    assert cfg.backend == "local-http"
    assert cfg.local_http_base_url == "http://localhost:5003"


def test_duration_seconds_defaults_to_30() -> None:
    cfg = MusicConfig()
    assert cfg.duration_seconds == 30.0
