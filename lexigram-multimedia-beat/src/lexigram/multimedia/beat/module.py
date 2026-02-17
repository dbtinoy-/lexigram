"""Beat-analysis module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.multimedia.protocols import BeatAnalysisProvider
from lexigram.di.module import DynamicModule, Module, module
from lexigram.multimedia.beat.config import BeatAnalysisConfig


@module()
class BeatAnalysisModule(Module):
    """Librosa/madmom tempo-and-beat-detection integration."""

    @classmethod
    def configure(cls, config: BeatAnalysisConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.beat.di.provider import BeatAnalysisGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[BeatAnalysisGenerationProvider(config=config)],
            exports=[BeatAnalysisProvider],
        )

    @classmethod
    def stub(cls, config: BeatAnalysisConfig | None = None) -> DynamicModule:
        from lexigram.multimedia.beat.di.provider import BeatAnalysisGenerationProvider

        return DynamicModule(
            module=cls,
            providers=[
                BeatAnalysisGenerationProvider(
                    config=config or BeatAnalysisConfig(backend="librosa")
                )
            ],
            exports=[BeatAnalysisProvider],
        )


__all__ = ["BeatAnalysisModule"]
