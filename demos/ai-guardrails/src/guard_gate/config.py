"""Configuration binding — loads this demo's application.yaml."""

from __future__ import annotations

from pathlib import Path

from lexigram.config.main import LexigramConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


def load_lex_config() -> LexigramConfig:
    """Load the demo's full ``LexigramConfig``."""
    return LexigramConfig.from_yaml(APP_YAML)


__all__ = ["APP_YAML", "load_lex_config"]
