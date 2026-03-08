"""Image generation module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import ImageProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.image.config import ImageConfig
from lexigram.multimedia.image.tasks import ImageGenerationTask


@module()
class ImageModule(Module):
    """Image generation integration."""

    @classmethod
    def configure(cls, config: ImageConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.image.di.provider import ImageGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[ImageGenerationProvider(config=config)],
            exports=[ImageProvider, ImageGenerationTask],
        )

    @classmethod
    def stub(cls, config: ImageConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.image.di.provider import ImageGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[
                ImageGenerationProvider(
                    config=config or ImageConfig(backend="local-http")
                )
            ],
            exports=[ImageProvider, ImageGenerationTask],
        )


__all__ = ["ImageModule"]
