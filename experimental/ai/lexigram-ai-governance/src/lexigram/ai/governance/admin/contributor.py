"""Admin contributor for the AI governance relay accounting surface.

The contributor surfaces relay usage, quota pressure, and settlement
failures from the governance billing stack into the admin dashboard.
Dependencies (the usage store and the reservation manager) are resolved
lazily from the DI container at boot; every surface renders an explicit
unavailable state when a dependency is missing and never reports zero
usage or quota as if it were measured.

Static definitions live in :mod:`.contributor_definitions`; widget
rendering lives in :mod:`.widget_renderers`.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.governance.admin.contributor_definitions import (
    _ACTIONS,
    _HEALTH_DEFS,
    _NAV_ITEMS,
    _PAGE_DEFS,
    _WIDGETS,
)
from lexigram.ai.governance.admin.contributor_definitions import (
    PERMISSION_LEDGER as PERMISSION_LEDGER,
)
from lexigram.ai.governance.admin.contributor_definitions import (
    PERMISSION_LOG_READ as PERMISSION_LOG_READ,
)
from lexigram.ai.governance.admin.contributor_definitions import (
    PERMISSION_READ as PERMISSION_READ,
)
from lexigram.ai.governance.admin.widget_renderers import (
    render_current_spend,
    render_quota_pressure,
    render_settlement_failures,
    render_token_dimensions,
)
from lexigram.ai.governance.relay_billing import (
    RelayReservationManager,
    RelayUsageReportService,
)
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import (
    HealthCheckNotFoundError,
    WidgetNotFoundError,
)
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.contracts.ai.governance import RelayUsageStoreProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.exceptions.container import ContainerError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts.admin.errors import AdminError
    from lexigram.contracts.admin.types import (
        AdminActionDefinition,
        AdminHealthDefinition,
        DashboardWidgetDefinition,
        ManagementPageDefinition,
        NavigationContribution,
    )
    from lexigram.contracts.admin.widget_content import WidgetContent

__all__ = ["GovernanceAdminContributor"]

logger = get_logger(__name__)


class GovernanceAdminContributor(BaseAdminContributor):
    """Admin contributor for AI governance relay accounting.

    Provides current-spend, token-dimension, quota-pressure, and
    settlement-failure widgets plus management pages for relay usage,
    quotas, and settlements.  Registered via the
    ``lexigram.admin.contributors`` entry point.
    """

    name = "ai-governance"
    display_name = "AI Governance"
    group = "ai"
    icon = "shield"
    priority = 58

    required_permissions = frozenset(
        {PERMISSION_READ, PERMISSION_LOG_READ, PERMISSION_LEDGER}
    )

    def __init__(self) -> None:
        self._container: Any = None
        self._store: RelayUsageStoreProtocol | None = None
        self._manager: RelayReservationManager | None = None
        self._action_handlers: dict[str, Any] = {}

    async def on_admin_boot(self, container: Any) -> None:
        """Resolve the billing store and reservation manager from DI.

        Widgets that depend on a missing service render an explicit
        unavailable ``MessageContent`` state rather than failing
        the whole admin boot — but the resolution failure itself is
        always logged so it isn't silently invisible in production.

        Args:
            container: The DI container resolver.
        """
        self._container = container
        try:
            self._store = await container.resolve(RelayUsageStoreProtocol)
        except ContainerError:
            logger.warning(
                "governance.dependency_unavailable",
                dependency="RelayUsageStoreProtocol",
            )
            self._store = None
        try:
            self._manager = await container.resolve(RelayReservationManager)
        except ContainerError:
            logger.warning(
                "governance.dependency_unavailable",
                dependency="RelayReservationManager",
            )
            self._manager = None
        self._action_handlers = {}
        for action in _ACTIONS:
            module_path, _, handler_name = action.handler.partition(":")
            module = import_module(module_path)
            self._action_handlers[action.name] = getattr(module, handler_name)

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return list(_PAGE_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return list(_ACTIONS)

    async def execute_action(
        self,
        action_name: str,
        params: dict[str, object],
    ) -> object:
        """Dispatch an action to its boot-resolved handler.

        Handlers run with the container captured at boot; a container is
        required.  Every handler performs server-side parameter
        validation before invoking the ledger service.

        Args:
            action_name: Name of the action to execute.
            params: Parameters forwarded to the action handler.

        Returns:
            The handler's result mapping.

        Raises:
            LookupError: Unknown action name.
            RuntimeError: Contributor booted without a container.
        """
        handler = self._action_handlers.get(action_name)
        if handler is None:
            raise LookupError(f"unknown ai-governance action {action_name!r}")
        if self._container is None:
            raise RuntimeError("contributor has no container; on_admin_boot required")
        return await handler(self._container, **params)

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        resolver: Any = None,
    ) -> Result[WidgetViewModel, AdminError]:
        """Render a named widget using handler registry dispatch.

        Args:
            widget_name: Name of the widget to render.
            params: Typed widget parameters.
            resolver: Optional container override; unused, services were
                resolved at boot.

        Returns:
            Ok(WidgetViewModel) with structured content on success;
            Err(WidgetNotFoundError) for unknown widget names.
        """
        renderers: dict[str, Callable[[WidgetParams], Any]] = {
            "current_spend": self._render_current_spend,
            "token_dimensions": self._render_token_dimensions,
            "quota_pressure": self._render_quota_pressure,
            "settlement_failures": self._render_settlement_failures,
        }
        renderer = renderers.get(widget_name)
        if renderer is None:
            not_found: Result[WidgetViewModel, AdminError] = cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError("ai-governance", widget_name)),
            )
            return not_found
        content = await renderer(params)
        return Ok(WidgetViewModel(content=content))

    async def render_health_check(
        self,
        check_name: str,
    ) -> Result[HealthCheckPayload, AdminError]:
        """Render the aggregate billing health check.

        Args:
            check_name: Name of the health check; only
                ``governance.billing`` is served.

        Returns:
            Ok(HealthCheckPayload) with availability status; Err when the
            check is unknown.
        """
        if check_name != "governance.billing":
            not_found: Result[HealthCheckPayload, AdminError] = cast(
                "Result[HealthCheckPayload, AdminError]",
                Err(HealthCheckNotFoundError("ai-governance", check_name)),
            )
            return not_found
        if self._store is None or self._manager is None:
            return Ok(
                HealthCheckPayload(
                    status=HealthStatus.DEGRADED,
                    component="AI Governance Billing",
                    detail=(
                        "degraded (billing store or reservation manager unavailable)"
                    ),
                )
            )
        return Ok(
            HealthCheckPayload(
                status=HealthStatus.HEALTHY,
                component="AI Governance Billing",
                detail="available",
            )
        )

    async def _reporter(self) -> RelayUsageReportService | None:
        """Return a report service over the resolved store, if any."""
        if self._store is None:
            return None
        return RelayUsageReportService(self._store)

    async def _render_current_spend(self, params: WidgetParams) -> WidgetContent:
        """Render the settled charge for the widget window."""
        return await render_current_spend(await self._reporter(), params)

    async def _render_token_dimensions(self, params: WidgetParams) -> WidgetContent:
        """Render prompt/completion/total tokens for the window."""
        return await render_token_dimensions(await self._reporter(), params)

    async def _render_quota_pressure(self, params: WidgetParams) -> WidgetContent:
        """Render remaining capacity per configured dimension."""
        del params
        return await render_quota_pressure(self._manager)

    async def _render_settlement_failures(self, params: WidgetParams) -> WidgetContent:
        """Render failed settlement counts in the widget window."""
        return await render_settlement_failures(await self._reporter(), params)
