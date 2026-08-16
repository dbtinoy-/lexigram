"""Tests for idempotency module."""

import pytest

from lexigram.di.module import DynamicModule
from lexigram.resilience.idempotency.module import IdempotencyModule


class TestIdempotencyModule:
    def test_idempotency_module_exists(self) -> None:
        assert IdempotencyModule is not None

    def test_configure_returns_dynamic_module(self) -> None:
        result = IdempotencyModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is IdempotencyModule

    def test_configure_exports_idempotency_store(self) -> None:
        from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol

        result = IdempotencyModule.configure(None)
        assert IdempotencyStoreProtocol in result.exports

    def test_configure_config_type_check(self) -> None:
        with pytest.raises(TypeError, match="must be IdempotencyConfig"):
            IdempotencyModule.configure(config="invalid")
