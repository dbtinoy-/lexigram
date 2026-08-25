"""Configuration binding for the MFA console demo.

Framework convention: run the console from its own directory so
``LexigramConfig`` auto-discovers ``application.yaml``; ``LEX_AUTH__*``
overrides and profiles apply via the loader.
"""

from __future__ import annotations

from lexigram.config.main import LexigramConfig


def load_lex_config() -> LexigramConfig:
    """Load the console's full ``LexigramConfig`` (web + auth sections)."""
    return LexigramConfig.from_yaml()


__all__ = ["load_lex_config"]
