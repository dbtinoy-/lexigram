"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pathlib

import pytest

from rbac_console.config import load_lex_config


def test_load_reads_auth_and_web_sections() -> None:
    from lexigram.auth.config import AuthConfig
    from lexigram.web.config import WebConfig

    config = load_lex_config()
    assert config.has_section("auth")
    assert config.has_section("web")

    auth = config.get_section("auth", AuthConfig)
    assert auth.secret_key.startswith("rbac-console-demo")

    web = config.get_section("web", WebConfig)
    assert web.server.port == 8090
    assert web.server.host == "127.0.0.1"
    assert web.security.csrf.enabled is False


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    from lexigram.web.config import WebConfig

    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7098")
    assert load_lex_config().get_section("web", WebConfig).server.port == 7098


def test_composition_root_contains_no_literal_server_config() -> None:
    app_src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "rbac_console"
        / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "8090" not in app_src
