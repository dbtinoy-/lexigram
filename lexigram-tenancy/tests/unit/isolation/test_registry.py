"""Tests for IsolationStrategyRegistry."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy


def test_register_and_get() -> None:
    """Registered strategy is retrievable by name."""
    registry = IsolationStrategyRegistry()
    strategy = RowLevelIsolationStrategy()
    registry.register(strategy)
    assert registry.get("row_level") is strategy


def test_get_unknown_raises_tenant_error() -> None:
    """Getting an unknown strategy raises TenantError."""
    registry = IsolationStrategyRegistry()
    with pytest.raises(TenantError, match="Unknown isolation strategy"):
        registry.get("nonexistent")


def test_with_defaults_includes_row_level() -> None:
    """with_defaults() pre-registers the row_level strategy."""
    registry = IsolationStrategyRegistry.with_defaults()
    strategy = registry.get("row_level")
    assert strategy.name == "row_level"


def test_names_returns_all_registered() -> None:
    """names() returns a list of all registered strategy names."""
    registry = IsolationStrategyRegistry.with_defaults()
    assert "row_level" in registry.names()


def test_register_multiple_strategies() -> None:
    """Can register multiple strategies with different names."""
    registry = IsolationStrategyRegistry()
    strategy1 = RowLevelIsolationStrategy()
    strategy1.name = "strategy1"
    strategy2 = RowLevelIsolationStrategy()
    strategy2.name = "strategy2"
    registry.register(strategy1)
    registry.register(strategy2)
    assert "strategy1" in registry.names()
    assert "strategy2" in registry.names()


def test_register_overwrites_existing() -> None:
    """Registering the same name twice overwrites the previous strategy."""
    registry = IsolationStrategyRegistry()
    strategy1 = RowLevelIsolationStrategy()
    strategy2 = RowLevelIsolationStrategy()
    registry.register(strategy1)
    registry.register(strategy2)
    strategies_by_name = registry.names()
    assert strategies_by_name.count("row_level") == 1


def test_empty_registry_has_no_names() -> None:
    """Empty registry returns empty list of names."""
    registry = IsolationStrategyRegistry()
    assert registry.names() == []


def test_empty_registry_get_raises() -> None:
    """Empty registry raises on get()."""
    registry = IsolationStrategyRegistry()
    with pytest.raises(TenantError, match="Unknown isolation strategy"):
        registry.get("anything")


def test_with_returns_correct_type() -> None:
    """with_defaults() returns IsolationStrategyRegistry instance."""
    registry = IsolationStrategyRegistry.with_defaults()
    assert isinstance(registry, IsolationStrategyRegistry)


def test_get_returns_protocol_type() -> None:
    """get() returns object implementing TenantIsolationStrategyProtocol."""
    from lexigram.contracts.tenancy.protocols import TenantIsolationStrategyProtocol
    registry = IsolationStrategyRegistry.with_defaults()
    strategy = registry.get("row_level")
    assert isinstance(strategy, TenantIsolationStrategyProtocol)
