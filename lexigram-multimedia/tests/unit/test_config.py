from lexigram.multimedia.audio_tts.config import TTSConfig
from lexigram.multimedia.config import MultimediaConfig


def test_default_config_has_all_four_subsystem_configs() -> None:
    cfg = MultimediaConfig()
    assert isinstance(cfg.tts, TTSConfig)
    assert cfg.storage_path_prefix == "multimedia/"
