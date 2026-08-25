"""Configuration binding for the MFA console demo.

Blueprint wiring: server and auth knobs live in ``application.yaml``; binding
is explicit against this demo's own file so behavior never depends on the
current working directory.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


def load_lex_config() -> LexigramConfig:
    """Load the console's full ``LexigramConfig`` (web + auth sections)."""
    return LexigramConfig.from_yaml(APP_YAML)


def bind_web() -> WebConfig:
    """Bind the ``web`` section for server wiring."""
    return LexigramConfig.from_yaml(APP_YAML).get_section("web", WebConfig)


__all__ = ["APP_YAML", "bind_web", "load_lex_config"]
