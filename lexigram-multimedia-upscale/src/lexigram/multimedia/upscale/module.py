"""Upscale generation module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import UpscaleProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.upscale.config import UpscaleConfig


@module()
class UpscaleModule(Module):
    """Image/video upscale integration."""

    @classmethod
    def configure(cls, config: UpscaleConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.upscale.di.provider import UpscaleGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[UpscaleGenerationProvider(config=config)],
            exports=[UpscaleProvider],
        )

    @classmethod
    def stub(cls, config: UpscaleConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.upscale.di.provider import UpscaleGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[
                UpscaleGenerationProvider(
                    config=config or UpscaleConfig(backend="real-esrgan")
                )
            ],
            exports=[UpscaleProvider],
        )


__all__ = ["UpscaleModule"]
