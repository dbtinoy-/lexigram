"""Lifecycle wiring for the Approval Flow showcase."""

from __future__ import annotations

from typing import TYPE_CHECKING

from approval_flow.config import ApprovalFlowConfig
from approval_flow.controllers.api import ApprovalFlowApiController
from approval_flow.services.flow import ApprovalFlowService
from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.workflow import StateMachineProtocol
from lexigram.di.provider import Provider
from lexigram.workflow.di.provider import WorkflowProvider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class ApprovalFlowProvider(Provider):
    """Bind the demo service after Lexigram WorkflowModule is registered."""

    name = "approval_flow"
    config_key: str | None = "approval_flow"
    config_model: type | None = ApprovalFlowConfig

    def __init__(self) -> None:
        super().__init__()
        self._service: ApprovalFlowService | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        cfg = self.config or ApprovalFlowConfig()
        container.singleton(ApprovalFlowConfig, instance=cfg)
        container.singleton(ApprovalFlowApiController, ApprovalFlowApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        # Resolving the package provider makes the composition/lifecycle
        # relationship explicit: this app's service comes after WorkflowModule.
        await container.resolve(WorkflowProvider)
        config = await container.resolve(ApprovalFlowConfig)
        state_machine = await container.resolve(StateMachineProtocol)
        self._service = ApprovalFlowService(config, state_machine=state_machine)
        container.bind(
            ApprovalFlowApiController,
            ApprovalFlowApiController(service=self._service),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY if self._service else HealthStatus.UNHEALTHY,
            category=HealthCheckCategory.READINESS,
        )


__all__ = ["ApprovalFlowProvider"]
