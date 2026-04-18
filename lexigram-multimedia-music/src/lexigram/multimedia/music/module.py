"""Music generation module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import MusicProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.music.config import MusicConfig


@module()
class AudioMusicModule(Module):
    """Music generation integration."""

    @classmethod
    def configure(cls, config: MusicConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.music.di.provider import AudioMusicProvider

        return DynamicModule(
            module=cls,
            providers=[AudioMusicProvider(config=config)],
            exports=[MusicProvider],
        )

    @classmethod
    def stub(cls, config: MusicConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.music.di.provider import AudioMusicProvider

        return DynamicModule(
            module=cls,
            providers=[
                AudioMusicProvider(config=config or MusicConfig(backend="local-http"))
            ],
            exports=[MusicProvider],
        )


__all__ = ["AudioMusicModule"]
