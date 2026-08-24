"""Module for the llm-reproducibility demo."""

from __future__ import annotations

from pathlib import Path

from lexigram.di.module import DynamicModule, Module, module
from llm_reproducibility.di.provider import ExperimentProvider


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
