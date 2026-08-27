"""Tests for demo-hub yaml binding."""

from __future__ import annotations

import pytest

from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig


def _load_web_config() -> WebConfig:
    """Load the web section from application.yaml (replaces deleted bind_web)."""
    from pathlib import Path

    yaml_path = Path(__file__).resolve().parent.parent / "application.yaml"
    return LexigramConfig.from_yaml(yaml_path).get_section("web", WebConfig)


def test_web_config_reads_server_and_security() -> None:
    web_config = _load_web_config()
    assert web_config.server.port == 7000
    assert web_config.server.host == "127.0.0.1"
    assert web_config.security.csrf.enabled is False


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7077")
    assert _load_web_config().server.port == 7077
