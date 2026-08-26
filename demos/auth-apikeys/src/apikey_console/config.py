"""Configuration binding for the API-keys console demo.

Blueprint wiring: server and auth knobs live in ``application.yaml``; binding
is explicit against this demo's own file (``__file__``-anchored) so behavior
never depends on the current working directory.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.config.main import LexigramConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


def load_lex_config() -> LexigramConfig:
    """Load the console's full ``LexigramConfig`` (web + auth sections)."""
    return LexigramConfig.from_yaml(APP_YAML)


__all__ = ["APP_YAML", "load_lex_config"]
