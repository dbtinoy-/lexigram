"""Unit tests for GovernanceModule dynamic wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.di.provider import GovernanceProvider
from lexigram.ai.governance.module import GovernanceModule
from lexigram.ai.governance.relay_billing.models import RelayBillingConfig
from lexigram.contracts.ai.governance import (
    AIGovernanceProtocol,
    CostTrackingProtocol,
    RelayBillingProtocol,
)
from lexigram.contracts.ai.relay import (
    RelayRequestLogStoreProtocol,
    RelayUsageServiceProtocol,
)
from lexigram.di.module import DynamicModule


class TestGovernanceModule:
    """Verify GovernanceModule.configure wiring and exports."""

    def test_configure_returns_dynamic_module(self) -> None:
        dynamic_module = GovernanceModule.configure()

        assert isinstance(dynamic_module, DynamicModule)
        assert dynamic_module.module is GovernanceModule
        assert len(dynamic_module.providers) == 1
        assert isinstance(dynamic_module.providers[0], GovernanceProvider)

    def test_configure_exports_governance_contract_protocols(self) -> None:
        from lexigram.ai.governance.exceptions import (
            BudgetExceededError,
            GovernanceError,
            ModelAccessDeniedError,
            RateLimitExceededError,
        )

        dynamic_module = GovernanceModule.configure()

        assert AIGovernanceProtocol in dynamic_module.exports
        assert CostTrackingProtocol in dynamic_module.exports
        assert GovernanceError in dynamic_module.exports
        assert BudgetExceededError in dynamic_module.exports
        assert RateLimitExceededError in dynamic_module.exports
        assert ModelAccessDeniedError in dynamic_module.exports

    @pytest.mark.asyncio
    async def test_configure_wires_dict_config_into_provider(self) -> None:
        dynamic_module = GovernanceModule.configure(
            {"enabled": False, "monthly_budget": 42.0}
        )
        provider = dynamic_module.providers[0]

        assert isinstance(provider, GovernanceProvider)

        container = MagicMock()
        container.singleton = MagicMock()

        await provider.register(container)

        assert container.singleton.call_count == 5
        expected = [
            GovernanceConfig,
            RelayBillingConfig,
            RelayBillingProtocol,
            RelayRequestLogStoreProtocol,
            RelayUsageServiceProtocol,
        ]
        for idx, want in enumerate(expected):
            assert container.singleton.call_args_list[idx].args[0] is want
        service_type, config = container.singleton.call_args_list[0].args
        assert service_type is GovernanceConfig
        assert isinstance(config, GovernanceConfig)
        assert config.enabled is False
        assert config.monthly_budget == 42.0

    @pytest.mark.asyncio
    async def test_configure_wires_governance_config_instance(self) -> None:
        config = GovernanceConfig(enabled=False, monthly_budget=99.0)
        dynamic_module = GovernanceModule.configure(config)
        provider = dynamic_module.providers[0]

        assert isinstance(provider, GovernanceProvider)

        container = MagicMock()
        container.singleton = MagicMock()

        await provider.register(container)

        service_type, resolved_config = container.singleton.call_args_list[0].args
        assert service_type is GovernanceConfig
        assert resolved_config is config

    def test_configure_rejects_invalid_config_type(self) -> None:
        with pytest.raises(TypeError, match="config must be GovernanceConfig or dict"):
            GovernanceModule.configure(config="invalid")
