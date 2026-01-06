"""Video generation module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import VideoProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.video.config import VideoConfig


@module()
class VideoModule(Module):
    """Video generation integration."""

    @classmethod
    def configure(cls, config: VideoConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.video.di.provider import VideoGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[VideoGenerationProvider(config=config)],
            exports=[VideoProvider],
        )

    @classmethod
    def stub(cls, config: VideoConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.video.di.provider import VideoGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[
                VideoGenerationProvider(
                    config=config or VideoConfig(backend="local-http")
                )
            ],
            exports=[VideoProvider],
        )


__all__ = ["VideoModule"]
