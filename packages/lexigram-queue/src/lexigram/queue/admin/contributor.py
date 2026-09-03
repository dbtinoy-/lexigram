"""Admin contributor for lexigram-queue — surfaces queue depth, consumer lag,
and failed-message widgets into the Lexigram admin dashboard.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from typing import Any, cast

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.contributor_boot import (
    summarize_contributor_boot_failure,
)
from lexigram.contracts.admin.errors import AdminError, WidgetNotFoundError
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    WidgetCategory,
    WidgetKind,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.admin.widget_protocols import WidgetHandlerProtocol
from lexigram.contracts.core.di import ContainerResolverProtocol
from lexigram.contracts.core.result import Result
from lexigram.logging import get_logger
from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
from lexigram.queue.admin.handlers.failed_messages import FailedMessagesWidgetHandler
from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler
from lexigram.result import Err, Ok

logger = get_logger(__name__)

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="queue_depth",
        title="Queue Depth",
        contributor="queue",
        render_endpoint="/admin/queue/widgets/queue_depth",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        view_kind=WidgetKind.STAT,
        description="Current number of messages waiting in all queues.",
    ),
    DashboardWidgetDefinition(
        name="consumer_lag",
        title="Consumer Lag",
        contributor="queue",
        render_endpoint="/admin/queue/widgets/consumer_lag",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        view_kind=WidgetKind.STAT,
        description="Lag between the latest message and the last consumed offset.",
    ),
    DashboardWidgetDefinition(
        name="failed_messages",
        title="Failed Messages",
        contributor="queue",
        render_endpoint="/admin/queue/widgets/failed_messages",
        size=WidgetSize.SMALL,
        category=WidgetCategory.HEALTH,
        view_kind=WidgetKind.STAT,
        description="Number of messages that failed processing and await retry.",
    ),
)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Queue",
        url="/admin/queue",
        icon="queue-list",
        group="infrastructure",
        order=35,
        children=(
            NavigationContribution(
                label="Jobs",
                url="/admin/queue/jobs",
                icon="briefcase",
                group="infrastructure",
                order=10,
            ),
            NavigationContribution(
                label="Consumers",
                url="/admin/queue/consumers",
                icon="cpu",
                group="infrastructure",
                order=20,
            ),
        ),
    ),
)

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="queue.broker",
        contributor="queue",
        component="Message Broker",
        check_endpoint="/admin/queue/health/broker",
        description="Verifies connectivity to the message broker.",
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="retry_failed",
        title="Retry Failed Messages",
        contributor="queue",
        handler="lexigram.queue.admin.actions:retry_failed",
        icon="refresh-cw",
        category="operations",
    ),
)


class QueueAdminContributor(BaseAdminContributor):
    """Admin contributor for the lexigram-queue package.

    Dependencies are resolved from the container in ``on_admin_boot``.
    """

    name = "queue"
    display_name = "Queue"
    group = "infrastructure"
    icon = "queue-list"
    priority = 35

    def __init__(self) -> None:
        """Initialize the queue admin contributor with no arguments."""
        self._handlers: dict[str, WidgetHandlerProtocol] = {}
        self._container: ContainerResolverProtocol | None = None
        self._action_handlers: dict[str, Any] = {}

    async def on_admin_boot(self, container: object) -> None:
        """Resolve queue admin dependencies from the DI container.

        Widget handlers are resolved per name; action handlers are
        imported from the ``module:attr`` paths declared in ``_ACTIONS``.

        Args:
            container: The DI container resolver.
        """
        typed_container = cast("ContainerResolverProtocol", container)
        self._container = typed_container
        self._handlers = {}
        try:
            depth_handler = await typed_container.resolve(QueueDepthWidgetHandler)
            lag_handler = await typed_container.resolve(ConsumerLagWidgetHandler)
            failed_handler = await typed_container.resolve(FailedMessagesWidgetHandler)
            self._handlers = {
                "queue_depth": depth_handler,
                "consumer_lag": lag_handler,
                "failed_messages": failed_handler,
            }
        except Exception as exc:  # noqa: BLE001
            failure = summarize_contributor_boot_failure(exc)
            if failure.expected:
                logger.info(
                    "admin.contributor_disabled",
                    contributor=self.name,
                    feature="widget handlers",
                    reason=failure.reason,
                    missing=failure.summary,
                )
            else:
                logger.warning(
                    "queue_contributor.handlers_unavailable",
                    error=failure.summary,
                    error_type=type(exc).__name__,
                    exc_info=True,
                )

        self._action_handlers = {}
        try:
            for action in _ACTIONS:
                module_path, _, handler_name = action.handler.partition(":")
                module = import_module(module_path)
                self._action_handlers[action.name] = getattr(module, handler_name)
        except Exception as exc:  # noqa: BLE001
            failure = summarize_contributor_boot_failure(exc)
            logger.warning(
                "queue_contributor.actions_unavailable",
                error=failure.summary,
                error_type=type(exc).__name__,
                exc_info=True,
            )

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return list(_ACTIONS)

    async def execute_action(
        self,
        action_name: str,
        params: dict[str, object],
    ) -> object:
        """Dispatch an action to its boot-resolved handler.

        Handlers run with the container captured at boot; a container is
        required.

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
            raise LookupError(f"unknown queue action {action_name!r}")
        if self._container is None:
            raise RuntimeError("contributor has no container; on_admin_boot required")
        return await handler(self._container, **params)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="queue_overview",
                title="Queue Overview",
                contributor="queue",
                route_path="/queue",
                handler="lexigram.queue.admin.pages.overview:QueueOverviewPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="queue-list",
                description="Queue depth, consumer lag, and failed message counts",
                order=10,
            ),
            ManagementPageDefinition(
                name="queue_jobs",
                title="Queue Jobs",
                contributor="queue",
                route_path="/queue/jobs",
                handler="lexigram.queue.admin.pages.jobs:QueueJobsPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="briefcase",
                description="Pending, processing, and completed jobs",
                order=20,
            ),
            ManagementPageDefinition(
                name="queue_consumers",
                title="Queue Consumers",
                contributor="queue",
                route_path="/queue/consumers",
                handler="lexigram.queue.admin.pages.consumers:QueueConsumersPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="cpu",
                description="Registered consumers and their status",
                order=30,
            ),
        ]

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        resolver: ContainerResolverProtocol | None = None,
    ) -> Result[WidgetViewModel, AdminError]:
        """Render a named widget using registry dispatch.

        Args:
            widget_name: Name of the widget to render.
            params: Typed widget parameters.

        Returns:
            Ok(WidgetViewModel) on success.
            Err(WidgetNotFoundError) if widget_name not served by this contributor.
            Infrastructure exceptions propagate.
        """
        if not self._handlers:
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError(self.name, widget_name)),
            )

        handler = self._handlers.get(widget_name)
        if handler is None:
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError(self.name, widget_name)),
            )

        data_result = await handler.get_data(params)
        if data_result.is_err():
            return Err(data_result.unwrap_err())

        content = data_result.unwrap()
        return cast(
            "Result[WidgetViewModel, AdminError]",
            Ok(WidgetViewModel(content=content)),
        )


__all__ = ["QueueAdminContributor"]
