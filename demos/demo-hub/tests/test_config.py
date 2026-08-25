"""Tests for demo-hub yaml binding (Blueprint)."""

from __future__ import annotations

import pytest

from demo_hub.config import bind_web


def test_bind_web_reads_server_and_security() -> None:
    web_config = bind_web()
    assert web_config.server.port == 7000
    assert web_config.server.host == "127.0.0.1"
    assert web_config.security.csrf.enabled is False


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7077")
    assert bind_web().server.port == 7077
