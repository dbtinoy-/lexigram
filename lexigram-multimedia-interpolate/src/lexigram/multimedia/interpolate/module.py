"""Interpolation module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import InterpolationProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.interpolate.config import InterpolationConfig


@module()
class InterpolationModule(Module):
    """RIFE frame-interpolation integration."""

    @classmethod
    def configure(cls, config: InterpolationConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.interpolate.di.provider import (
            InterpolationGenerationProvider,
        )

        return DynamicModule(
            module=cls,
            providers=[InterpolationGenerationProvider(config=config)],
            exports=[InterpolationProvider],
        )

    @classmethod
    def stub(cls, config: InterpolationConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.interpolate.di.provider import (
            InterpolationGenerationProvider,
        )

        return DynamicModule(
            module=cls,
            providers=[
                InterpolationGenerationProvider(
                    config=config or InterpolationConfig(backend="rife")
                )
            ],
            exports=[InterpolationProvider],
        )


__all__ = ["InterpolationModule"]
