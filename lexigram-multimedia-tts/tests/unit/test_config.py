from lexigram.multimedia.tts.config import TTSConfig


def test_default_backend_is_local_http() -> None:
    cfg = TTSConfig()
    assert cfg.backend == "local-http"
    assert cfg.local_http_base_url == "http://localhost:5002"


def test_elevenlabs_backend_requires_voice_id_at_use_not_construction() -> None:
    cfg = TTSConfig(backend="elevenlabs", elevenlabs_voice_id="abc123")
    assert cfg.backend == "elevenlabs"
    assert cfg.elevenlabs_voice_id == "abc123"
