"""Configuration binding for the demo hub.

Blueprint wiring: the hub is pure composition and defines no demo-specific
knobs, so only the framework ``web`` section is bound. Binding is explicit
against this demo's own ``application.yaml`` (``__file__``-anchored) because
provider auto-injection resolves configuration from the current working
directory and cannot be trusted for demos run from a repository root.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


def load_lex_config() -> LexigramConfig:
    """Load the hub's full ``LexigramConfig`` from application.yaml."""
    return LexigramConfig.from_yaml(APP_YAML)


def bind_web() -> WebConfig:
    """Bind the ``web`` section for server wiring."""
    return LexigramConfig.from_yaml(APP_YAML).get_section("web", WebConfig)


__all__ = ["APP_YAML", "bind_web", "load_lex_config"]
