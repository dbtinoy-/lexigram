"""Configuration binding for the resilient-rates demo.

Loads ``application.yaml`` from this package (``__file__``-anchored) so
behavior never depends on the process working directory; ``LEX_``
environment overrides and ``LEX_PROFILE`` overlays still apply through the
loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexigram.config.main import LexigramConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


@dataclass(frozen=True)
class RatesConfig:
    """Typed ``demo:`` section of the resilient-rates application.yaml.

    Attributes:
        upstream_scenario: Initial upstream health scenario
            (``healthy | flaky | down | slow``).
    """

    upstream_scenario: str = "healthy"


def load_lex_config() -> LexigramConfig:
    """Load the demo's full ``LexigramConfig`` from application.yaml."""
    return LexigramConfig.from_yaml(APP_YAML)


__all__ = ["APP_YAML", "RatesConfig", "load_lex_config"]
