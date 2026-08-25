"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pathlib

import pytest

from ops_console.config import RealtimeConfig, bind_application


def test_bind_application_reads_web_and_demo_sections() -> None:
    web_config, demo_config = bind_application()
    assert web_config.server.port == 7071
    assert web_config.server.host == "127.0.0.1"
    assert web_config.security.csrf.enabled is False
    assert demo_config.heartbeat_interval_seconds == 15
    assert demo_config.history_size == 100
    assert demo_config.queue_capacity == 100


def test_env_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    monkeypatch.setenv("LEX_DEMO__HEARTBEAT_INTERVAL_SECONDS", "1.5")
    web_config, demo_config = bind_application()
    assert web_config.server.port == 7099
    assert demo_config.heartbeat_interval_seconds == 1.5


def test_composition_root_contains_no_literal_server_config() -> None:
    app_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "ops_console" / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "7071" not in app_src
