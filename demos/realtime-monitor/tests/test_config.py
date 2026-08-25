"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pathlib

import pytest

from lexigram.web.config import WebConfig

from ops_console.config import RealtimeConfig


def test_demo_section_self_binds_with_defaults() -> None:
    demo = RealtimeConfig.from_yaml()
    assert demo.heartbeat_interval_seconds == 15
    assert demo.history_size == 100
    assert demo.queue_capacity == 100


def test_env_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    monkeypatch.setenv("LEX_DEMO__HEARTBEAT_INTERVAL_SECONDS", "1.5")

    web = WebConfig.from_yaml()
    demo = RealtimeConfig.from_yaml()

    assert web.server.port == 7099
    assert demo.heartbeat_interval_seconds == 1.5


def test_composition_root_contains_no_literal_server_config() -> None:
    app_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "ops_console" / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "7071" not in app_src
