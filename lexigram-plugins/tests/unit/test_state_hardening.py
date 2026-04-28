"""Error-path tests for plugin state persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from lexigram.contracts.exceptions.infra import InfrastructureError
from lexigram.plugins.exceptions import PluginStateError


def test_plugin_state_error_is_an_infrastructure_error() -> None:
    assert issubclass(PluginStateError, InfrastructureError)


def test_plugin_state_error_carries_structured_message(tmp_path: Path) -> None:
    err = PluginStateError("cannot write plugin state", path=str(tmp_path / "p.json"))
    assert "cannot write plugin state" in str(err)