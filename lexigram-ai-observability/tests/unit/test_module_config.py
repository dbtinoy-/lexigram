"""Config handling tests for ObservabilityModule."""

from __future__ import annotations

import pytest

from lexigram.ai.observability.config import ObservabilityConfig
from lexigram.ai.observability.module import ObservabilityModule


def test_stub_honors_typed_config() -> None:
    config = ObservabilityConfig(tracing_enabled=False)
    result = ObservabilityModule.stub(config=config)
    assert result.providers[0]._config is config


def test_stub_honors_dict_config() -> None:
    result = ObservabilityModule.stub(config={"tracing_enabled": False})
    assert result.providers[0]._config.tracing_enabled is False


def test_stub_default_config() -> None:
    result = ObservabilityModule.stub()
    assert result.providers[0]._config is not None


def test_stub_rejects_invalid_config_type() -> None:
    with pytest.raises(TypeError):
        ObservabilityModule.stub(config="invalid")