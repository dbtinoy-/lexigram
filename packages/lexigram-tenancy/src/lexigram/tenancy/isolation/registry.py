"""Isolation strategy registry."""

from __future__ import annotations

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.contracts.tenancy.protocols import TenantIsolationStrategyProtocol


class IsolationStrategyRegistry:
    """Registry of :class:`~lexigram.contracts.tenancy.protocols.TenantIsolationStrategyProtocol`
    implementations keyed by ``strategy.name``.

    Supports per-tenant strategy assignment via :meth:`set_tenant_strategy`
    and :meth:`get_tenant_strategy` for tier migration scenarios.

    Usage::

        registry = IsolationStrategyRegistry.with_defaults()
        strategy = registry.get("row_level")
        await strategy.provision_isolation("tenant-abc")
    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._strategies: dict[str, TenantIsolationStrategyProtocol] = {}
        self._tenant_strategies: dict[str, str] = {}

    def register(self, strategy: TenantIsolationStrategyProtocol) -> None:
        """Register an isolation strategy.

        Args:
            strategy: Strategy object with a ``name`` attribute.
        """
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> TenantIsolationStrategyProtocol:
        """Retrieve a strategy by name.

        Args:
            name: The strategy name (e.g. ``"row_level"``).

        Returns:
            The registered strategy.

        Raises:
            TenantError: If no strategy with the given name is registered.
        """
        strategy = self._strategies.get(name)
        if not strategy:
            raise TenantError(f"Unknown isolation strategy: {name}")
        return strategy

    def names(self) -> list[str]:
        """Return the names of all registered strategies.

        Returns:
            List of strategy name strings.
        """
        return list(self._strategies.keys())

    def set_tenant_strategy(self, tenant_id: str, strategy_name: str) -> None:
        """Assign an isolation strategy to a specific tenant.

        Used during tier migration to cut over a tenant to its new isolation
        level.  The strategy must already be registered.

        Args:
            tenant_id: The tenant identifier.
            strategy_name: The strategy name to assign.

        Raises:
            TenantError: If the strategy is not registered.
        """
        self.get(strategy_name)
        self._tenant_strategies[tenant_id] = strategy_name

    def get_tenant_strategy(
        self, tenant_id: str, default: str | None = None
    ) -> str | None:
        """Return the strategy name assigned to a tenant, or *default*.

        Args:
            tenant_id: The tenant identifier.
            default: Fallback value when no assignment exists.

        Returns:
            The assigned strategy name, or *default*.
        """
        return self._tenant_strategies.get(tenant_id, default)

    @classmethod
    def _default_entries(cls) -> dict[str, TenantIsolationStrategyProtocol]:
        """Declare the built-in isolation strategies.

        Schema and database strategies are NOT included because they require
        lexigram-sql and environment-specific provisioning logic.

        Returns:
            Only ``"row_level"`` by default.
        """
        from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy

        strategy = RowLevelIsolationStrategy()
        return {strategy.name: strategy}

    @classmethod
    def with_defaults(cls) -> IsolationStrategyRegistry:
        """Create a registry pre-populated with the row-level strategy."""
        registry = cls()
        for strategy in cls._default_entries().values():
            registry.register(strategy)
        return registry


__all__ = ["IsolationStrategyRegistry"]
