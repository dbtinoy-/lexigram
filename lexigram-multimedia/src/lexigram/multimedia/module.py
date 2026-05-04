"""Umbrella module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.multimedia.protocols import (
    BeatAnalysisProvider,
    ImageProvider,
    InterpolationProvider,
    MusicProvider,
    TTSProvider,
    UpscaleProvider,
    VideoProvider,
)
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.config import MultimediaConfig


@module()
class MultimediaModule(Module):
    """Audio/video/image generation: TTS, music, video, image, upscale,
    interpolate, and beat-analysis subsystems.
    """

    @classmethod
    def configure(cls, config: MultimediaConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.di.provider import MultimediaProvider

        return DynamicModule(
            module=cls,
            providers=[MultimediaProvider(config=config)],
            exports=[
                TTSProvider,
                MusicProvider,
                VideoProvider,
                ImageProvider,
                UpscaleProvider,
                InterpolationProvider,
                BeatAnalysisProvider,
            ],
        )

    @classmethod
    def stub(cls, config: MultimediaConfig | None = None) -> DynamicModule:
        from importlib.metadata import entry_points

        stub_imports: list[Any] = []
        for ep in entry_points(group="lexigram.multimedia.modules"):
            try:
                module_cls = ep.load()
                stub_imports.append(module_cls.stub())
            except (AttributeError, ImportError, RuntimeError):
                pass

        return DynamicModule(
            module=cls,
            imports=stub_imports,
            exports=[
                TTSProvider,
                MusicProvider,
                VideoProvider,
                ImageProvider,
                UpscaleProvider,
                InterpolationProvider,
                BeatAnalysisProvider,
            ],
        )


__all__ = ["MultimediaModule"]
