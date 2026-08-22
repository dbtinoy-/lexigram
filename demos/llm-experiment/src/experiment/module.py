"""Module for the llm-experiment demo."""

from __future__ import annotations

from pathlib import Path

from experiment.di.provider import ExperimentProvider
from lexigram.di.module import DynamicModule, Module, module


@module()
class ExperimentModule(Module):
    """Root module: seeded experiment runner + JSON metrics sink."""

    @classmethod
    def configure(cls, runs_dir: Path | None = None) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[ExperimentProvider(runs_dir=runs_dir)],
            exports=[],
        )


__all__ = ["ExperimentModule"]
