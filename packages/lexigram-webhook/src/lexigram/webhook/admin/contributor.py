"""Admin dashboard contributor for webhook management."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lexigram.contracts.admin import BaseAdminContributor
from lexigram.contracts.admin.types import (
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
)
from lexigram.contracts.core.di import ContainerResolverProtocol
from lexigram.logging.factory import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.webhook.protocols import (
        WebhookDeliveryStoreProtocol,
        WebhookSubscriptionStoreProtocol,
    )
    from lexigram.webhook.config import WebhookConfig

logger = get_logger(__name__)

__all__ = ["WebhookAdminContributor"]

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Webhooks",
        url="/admin/webhooks",
        icon="webhook",
        group="integrations",
        order=50,
        children=(
            NavigationContribution(
                label="Subscriptions",
                url="/admin/webhooks/subscriptions",
                icon="webhook",
                group="integrations",
                order=10,
            ),
            NavigationContribution(
                label="Deliveries",
                url="/admin/webhooks/deliveries",
                icon="send",
                group="integrations",
                order=20,
            ),
            NavigationContribution(
                label="Dead Letter",
                url="/admin/webhooks/dead-letters",
                icon="alert-triangle",
                group="integrations",
                order=30,
            ),
        ),
    ),
)


class WebhookAdminContributor(BaseAdminContributor):
    """Admin dashboard contributor for webhook management.

    Registers webhook management sections in the Lexigram admin panel.
    Dependencies are resolved from the DI container during ``on_admin_boot``.
    """

    name = "webhooks"
    display_name = "Webhooks"
    group = "integrations"
    icon = "webhook"
    priority = 50

    def __init__(self) -> None:
        """Initialize with no dependencies — resolved on boot."""
        self._subscription_store: WebhookSubscriptionStoreProtocol | None = None
        self._delivery_store: WebhookDeliveryStoreProtocol | None = None
        self._config: WebhookConfig | None = None
        self._root_resolver: ContainerResolverProtocol | None = None

    def attach_resolver(self, resolver: ContainerResolverProtocol) -> None:
        """Attach the root boot-phase resolver for dependency resolution.

        The webhook module's exports are visible in this resolver's scope,
        whereas the admin-scoped resolver passed to :meth:`on_admin_boot`
        cannot see them.

        Args:
            resolver: Root container resolver captured at provider boot.
        """
        self._root_resolver = resolver

    async def on_admin_boot(self, container: ContainerResolverProtocol | None) -> None:
        """Resolve dependencies from the DI container.

        Prefers the root resolver attached by
        :class:`~lexigram.webhook.di.sub_providers.admin_provider.WebhookAdminProvider`;
        falls back to the admin-scoped one.

        Args:
            container: The admin-scoped container resolver.
        """
        if container is None and self._root_resolver is None:
            return
        from lexigram.contracts.webhook.protocols import (
            WebhookDeliveryStoreProtocol,
            WebhookSubscriptionStoreProtocol,
        )
        from lexigram.webhook.config import WebhookConfig

        resolver = self._root_resolver or container
        if resolver is None:  # narrowed above; keeps mypy honest
            return

        try:
            self._subscription_store = await resolver.resolve(
                WebhookSubscriptionStoreProtocol
            )
            self._delivery_store = await resolver.resolve(WebhookDeliveryStoreProtocol)
            self._config = await resolver.resolve(WebhookConfig)
        except Exception:  # noqa: BLE001
            logger.warning("webhook.admin_contributor_boot_failed", exc_info=True)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        """Return the navigation items for this contributor."""
        return list(_NAV_ITEMS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        """Return the management page definitions for this contributor."""
        return [
            ManagementPageDefinition(
                name="webhooks_subscriptions",
                title="Webhook Subscriptions",
                contributor="webhooks",
                route_path="/webhooks/subscriptions",
                handler="lexigram.webhook.admin.pages.subscriptions:WebhookSubscriptionsPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="webhook",
                description="Manage webhook subscriptions",
                order=10,
            ),
            ManagementPageDefinition(
                name="webhooks_deliveries",
                title="Webhook Deliveries",
                contributor="webhooks",
                route_path="/webhooks/deliveries",
                handler="lexigram.webhook.admin.pages.deliveries:WebhookDeliveriesPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="send",
                description="View webhook delivery history",
                order=20,
            ),
            ManagementPageDefinition(
                name="webhooks_dead_letters",
                title="Webhook Dead Letters",
                contributor="webhooks",
                route_path="/webhooks/dead-letters",
                handler="lexigram.webhook.admin.pages.dead_letter:WebhookDeadLetterPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="alert-triangle",
                description="Dead-letter queue inspection",
                order=30,
            ),
        ]

    async def endpoint_health(self) -> dict[str, object]:
        """Return health metrics for the webhook system.

        Returns:
            Dict with subscription and dead-letter counts.
        """
        subscriptions = (
            await self._subscription_store.list(active_only=False, limit=10000)
            if self._subscription_store
            else []
        )
        active_count = sum(1 for s in subscriptions if s.active)
        dead_letters = (
            await self._delivery_store.get_dead_letters(limit=10000)
            if self._delivery_store
            else []
        )
        return {
            "total_subscriptions": len(subscriptions),
            "active_subscriptions": active_count,
            "dead_letter_count": len(dead_letters),
        }
