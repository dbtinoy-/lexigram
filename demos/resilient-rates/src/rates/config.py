"""Demo configuration bound from ``application.yaml``.

Framework convention (exemplar: ``lexigram-cache/config``): the config class
declares its section and self-binds via ``from_yaml`` — no explicit
``get_section`` calls anywhere. ``LEX_RATES__*`` overrides and
``LEX_PROFILE`` overlays apply through the loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import Field

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


@dataclass(init=False)
class RatesConfig(BaseConfig):
    """Typed ``demo:`` section of the resilient-rates application.yaml."""

    config_section: ClassVar[str] = "demo"

    upstream_scenario: str = Field(
        "healthy",
        description="Initial upstream scenario (healthy|flaky|down|slow)",
    )


__all__ = ["APP_YAML", "RatesConfig"]
