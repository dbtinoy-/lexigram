"""Demo configuration — ``demo:`` section of application.yaml.

Framework convention: run the demo from its own directory so
``LexigramConfig``/``from_yaml`` auto-discovers ``application.yaml``.
``LEX_RATES__*`` overrides and ``LEX_PROFILE`` overlays apply via the loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import Field


@dataclass(init=False)
class RatesConfig(BaseConfig):
    """Typed ``demo:`` section of the resilient-rates application.yaml."""

    config_section: ClassVar[str] = "demo"

    upstream_scenario: str = Field(
        "healthy",
        description="Initial upstream scenario (healthy|flaky|down|slow)",
    )


__all__ = ["RatesConfig"]
