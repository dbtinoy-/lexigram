"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pathlib

import pytest

from ops_console.config import RealtimeConfig, load_lex_config


def test_load_reads_web_and_demo_sections() -> None:
    config = load_lex_config()
    assert config.has_section("web")
    demo = config.get_section("demo", RealtimeConfig)
    assert demo.heartbeat_interval_seconds == 15
    assert demo.history_size == 100
    assert demo.queue_capacity == 100


def test_env_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    from lexigram.web.config import WebConfig

    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    monkeypatch.setenv("LEX_DEMO__HEARTBEAT_INTERVAL_SECONDS", "1.5")

    config = load_lex_config()
    web = config.get_section("web", WebConfig)
    demo = config.get_section("demo", RealtimeConfig)

    assert web.server.port == 7099
    assert demo.heartbeat_interval_seconds == 1.5


def test_composition_root_contains_no_literal_server_config() -> None:
    app_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "ops_console" / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "7071" not in app_src
