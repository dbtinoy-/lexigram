"""Governance module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.governance import (
    AIGovernanceProtocol,
    CostTrackingProtocol,
)
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.governance.config import GovernanceConfig


@module()
class GovernanceModule(Module):
    """AI Governance policy enforcement and cost-tracking integration.

    Call :meth:`configure` to register
    :class:`~lexigram.contracts.ai.governance.AIGovernanceProtocol` and
    :class:`~lexigram.contracts.ai.governance.CostTrackingProtocol`
    implementations for injection.

    Usage::

        from lexigram.ai.governance.config import GovernanceConfig

        @module(
            imports=[
                GovernanceModule.configure(
                    GovernanceConfig(monthly_budget=100.0)
                )
            ]
        )
        class AppModule(Module):
            pass

    Error Handling::

        Governance violations surface as typed exceptions that can be caught
        directly or handled via the Result pattern::

            from lexigram.ai.governance.exceptions import (
                GovernanceError,       # base — catch-all
                BudgetExceededError,   # monthly spend cap breached
                RateLimitExceededError,# RPM / TPM limit exceeded
                ModelAccessDeniedError,# policy denied model access
            )

    Exports:
        :class:`~lexigram.contracts.ai.governance.AIGovernanceProtocol`,
        :class:`~lexigram.contracts.ai.governance.CostTrackingProtocol`,
        :class:`~lexigram.ai.governance.exceptions.GovernanceError`,
        :class:`~lexigram.ai.governance.exceptions.BudgetExceededError`,
        :class:`~lexigram.ai.governance.exceptions.RateLimitExceededError`,
        :class:`~lexigram.ai.governance.exceptions.ModelAccessDeniedError`
    """

    @classmethod
    def configure(cls, config: GovernanceConfig | None = None) -> DynamicModule:
        """Create a GovernanceModule with the given configuration.

        Args:
            config: :class:`~lexigram.ai.governance.config.GovernanceConfig`,
                a plain ``dict`` of the same keys, or ``None`` to read from
                environment variables.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.

        Raises:
            TypeError: If *config* is not a ``GovernanceConfig``, ``dict``,
                or ``None``.
        """
        from lexigram.ai.governance.di.provider import GovernanceProvider
        from lexigram.ai.governance.exceptions import (
            BudgetExceededError,
            GovernanceError,
            ModelAccessDeniedError,
            RateLimitExceededError,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
            ResourceQuota,
            ResourceUnit,
            ResourceUsageResult,
            ResourceUsageSnapshot,
            ResourceWindowKind,
        )

        return DynamicModule(
            module=cls,
            providers=[GovernanceProvider(config=config)],
            exports=[
                AIGovernanceProtocol,
                CostTrackingProtocol,
                GovernanceError,
                BudgetExceededError,
                RateLimitExceededError,
                ModelAccessDeniedError,
                ResourceExhaustedError,
                ResourceQuota,
                ResourceUnit,
                ResourceUsageResult,
                ResourceUsageSnapshot,
                ResourceWindowKind,
            ],
        )

    @classmethod
    def stub(cls, config: GovernanceConfig | None = None) -> DynamicModule:
        """Create a GovernanceModule suitable for unit and integration testing.

        Uses in-memory or no-op implementations with minimal side effects.

        Args:
            config: Optional config override. Uses safe test defaults when None.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.governance.di.provider import GovernanceProvider
        from lexigram.ai.governance.exceptions import (
            BudgetExceededError,
            GovernanceError,
            ModelAccessDeniedError,
            RateLimitExceededError,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
            ResourceQuota,
            ResourceUnit,
            ResourceUsageResult,
            ResourceUsageSnapshot,
            ResourceWindowKind,
        )

        return DynamicModule(
            module=cls,
            providers=[GovernanceProvider(config=config)],
            exports=[
                AIGovernanceProtocol,
                CostTrackingProtocol,
                GovernanceError,
                BudgetExceededError,
                RateLimitExceededError,
                ModelAccessDeniedError,
                ResourceExhaustedError,
                ResourceQuota,
                ResourceUnit,
                ResourceUsageResult,
                ResourceUsageSnapshot,
                ResourceWindowKind,
            ],
        )


__all__ = ["GovernanceModule"]
