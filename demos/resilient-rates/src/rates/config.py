"""Demo configuration — ``demo:`` section of application.yaml.

Convention followed: **Yaml-first config** — ``LexigramConfig`` /
``from_yaml`` auto-discovers ``application.yaml`` from the working
directory.  ``LEX_DEMO__*`` overrides and ``LEX_PROFILE`` overlays apply
via the loader.

The ``RatesConfig`` dataclass declares the typed ``demo:`` section with
field-level defaults.  Environment variable overrides use the double-
underscore convention: ``LEX_DEMO__UPSTREAM_SCENARIO=down`` sets
``upstream_scenario = "down"``.
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
    name: str = "demo"
    enabled: bool = True

    upstream_scenario: str = Field(
        "healthy",
        description="Initial upstream scenario (healthy|flaky|down|slow)",
    )


__all__ = ["RatesConfig"]
