"""CLI health checks for lexigram-notification."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def check_notification_channels(
    container: ContainerResolverProtocol,
) -> dict[str, object]:
    """Check that notification channels are reachable.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {
        "status": "healthy",
        "message": "Notification channel health check not yet implemented",
    }
