"""Tests for optional integration detection helpers."""

from __future__ import annotations

from typing import Any

from lexigram.admin.integrations._optional import is_installed, require_or_noop


class DummyNoop:
    pass


class TestIsInstalled:
    def test_for_present_module(self) -> None:
        assert is_installed("lexigram.contracts") is True

    def test_for_missing_module(self) -> None:
        assert is_installed("lexigram.does_not_exist") is False


class TestRequireOrNoop:
    def test_returns_none_when_installed(self) -> None:
        result = require_or_noop("lexigram.contracts", DummyNoop)
        assert result is None

    def test_returns_noop_when_not_installed(self, capsys: Any) -> None:
        result = require_or_noop("lexigram.does_not_exist", DummyNoop)
        assert isinstance(result, DummyNoop)
        captured = capsys.readouterr()
        assert "not installed; using no-op" in captured.out
