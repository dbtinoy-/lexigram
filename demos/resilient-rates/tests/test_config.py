"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pytest

from lexigram.web import WebConfig
from rates.config import RatesConfig


def test_web_self_binds_server_and_security(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    web = WebConfig.from_yaml()
    assert web.server.port == 7099
    assert web.server.host == "127.0.0.1"
    assert web.security.csrf.enabled is False


def test_demo_section_self_binds_with_defaults() -> None:
    demo = RatesConfig.from_yaml()
    assert demo.upstream_scenario == "healthy"


def test_demo_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_DEMO__UPSTREAM_SCENARIO", "down")
    assert RatesConfig.from_yaml().upstream_scenario == "down"


def test_composition_root_contains_no_literal_server_config() -> None:
    import pathlib

    app_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "rates" / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "7073" not in app_src
