"""Tests for yaml-first configuration binding (Blueprint)."""

from __future__ import annotations

import pytest

from rbac_console.config import bind_web


def test_bind_web_reads_server_and_security() -> None:
    web_config = bind_web()
    assert web_config.server.port == 8090
    assert web_config.server.host == "127.0.0.1"
    assert web_config.security.csrf.enabled is False


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7098")
    assert bind_web().server.port == 7098


def test_module_contains_no_literal_server_config() -> None:
    import pathlib

    module_src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "rbac_console"
        / "module.py"
    ).read_text()
    assert "ServerConfig(" not in module_src
    assert "SecurityConfig(" not in module_src
    assert "8090" not in module_src
