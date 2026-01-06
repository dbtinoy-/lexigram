"""TTS module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import TTSProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.audio_tts.config import TTSConfig


@module()
class AudioTTSModule(Module):
    """Text-to-speech generation integration."""

    @classmethod
    def configure(cls, config: TTSConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.audio_tts.di.provider import AudioTTSProvider

        return DynamicModule(
            module=cls,
            providers=[AudioTTSProvider(config=config)],
            exports=[TTSProvider],
        )

    @classmethod
    def stub(cls, config: TTSConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.audio_tts.di.provider import AudioTTSProvider

        return DynamicModule(
            module=cls,
            providers=[
                AudioTTSProvider(config=config or TTSConfig(backend="local-http"))
            ],
            exports=[TTSProvider],
        )


__all__ = ["AudioTTSModule"]
