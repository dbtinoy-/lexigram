from lexigram.config import BaseConfig
from lexigram.multimedia.tts.config import TTSConfig


def test_tts_config_is_a_base_config() -> None:
    assert issubclass(TTSConfig, BaseConfig)
    assert TTSConfig.config_section == "multimedia_tts"


def test_tts_config_from_dict() -> None:
    cfg = TTSConfig.from_dict({"backend": "piper", "timeout": 10.0})
    assert cfg.backend == "piper"
    assert cfg.timeout == 10.0


def test_tts_config_to_safe_dict_redacts_secrets() -> None:
    cfg = TTSConfig(
        backend="elevenlabs",
        elevenlabs_api_key_secret_name="lex_my_elevenlabs_key",
    )
    safe = cfg.to_safe_dict()
    assert safe["elevenlabs_api_key_secret_name"] == "***"


def test_default_backend_is_local_http() -> None:
    cfg = TTSConfig()
    assert cfg.backend == "local-http"
    assert cfg.local_http_base_url == "http://localhost:5002"


def test_elevenlabs_backend_requires_voice_id_at_use_not_construction() -> None:
    cfg = TTSConfig(backend="elevenlabs", elevenlabs_voice_id="abc123")
    assert cfg.backend == "elevenlabs"
    assert cfg.elevenlabs_voice_id == "abc123"


def test_new_backends_have_working_defaults() -> None:
    cfg = TTSConfig()
    assert cfg.openai_voice == "alloy"
    assert cfg.openai_model == "tts-1"
    assert cfg.openai_base_url == "https://api.openai.com"
    assert cfg.chatterbox_base_url == "http://localhost:5100"
    assert cfg.chatterbox_exaggeration == 0.5
    assert cfg.chatterbox_cfg_weight == 0.5
    assert cfg.chatterbox_temperature == 0.85
    assert cfg.kokoro_base_url == "http://localhost:5101"
    assert cfg.kokoro_default_voice == "af_heart"
    assert cfg.f5_tts_base_url == "http://localhost:5102"
    assert cfg.piper_base_url == "http://localhost:5103"
    assert cfg.piper_default_voice == "en_US-lessac-medium"


def test_backend_literal_accepts_all_new_engines() -> None:
    for backend in ("chatterbox", "kokoro", "f5-tts", "piper"):
        cfg = TTSConfig(backend=backend)  # type: ignore[arg-type]
        assert cfg.backend == backend
