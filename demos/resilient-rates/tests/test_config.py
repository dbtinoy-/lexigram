"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pytest

from rates.config import RatesConfig, load_lex_config


def test_load_reads_web_cache_and_demo_sections() -> None:
    config = load_lex_config()

    assert config.has_section("web")
    assert config.has_section("cache")

    demo = config.get_section("demo", RatesConfig)
    assert demo.upstream_scenario == "healthy"


def test_web_server_values_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    from lexigram.web.config import WebConfig

    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    web = load_lex_config().get_section("web", WebConfig)
    assert web.server.port == 7099
    assert web.server.host == "127.0.0.1"
    assert web.security.csrf.enabled is False


def test_demo_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_DEMO__UPSTREAM_SCENARIO", "down")
    demo = load_lex_config().get_section("demo", RatesConfig)
    assert demo.upstream_scenario == "down"


def test_composition_root_contains_no_literal_server_config() -> None:
    import pathlib

    app_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "rates" / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "7073" not in app_src
