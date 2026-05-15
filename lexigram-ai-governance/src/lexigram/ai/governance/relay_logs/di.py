"""DI registrations and gateway hooks for relay request logs.

The governance provider root keeps the log store/sink hierarchy
unbound during ``register()`` (the store needs a database that is only
resolvable in ``boot()``).  :func:`boot_relay_logs` resolves the
database through its contract, builds the SQL store and usage service,
and binds them so the relay gateway's best-effort logger and the admin
read surface resolve the same instances through the container.

Nothing in this module imports gateway implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.governance import GovernanceConfig
from lexigram.ai.governance.relay_logs import (
    RelayUsageService,
    SqlRelayRequestLogStore,
)
from lexigram.contracts.ai.relay import (
    RelayDailyUsage,
    RelayModelRank,
    RelayRequestLogEntry,
    RelayRequestLogStoreProtocol,
    RelayUsageServiceProtocol,
)
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)

__all__ = [
    "NoopRelayRequestLogStore",
    "NoopRelayUsageService",
    "boot_relay_logs",
    "register_relay_logs",
]


class NoopRelayRequestLogStore(RelayRequestLogStoreProtocol):
    """Drop-everything request-log sink used when logging is disabled."""

    async def append(self, entry: RelayRequestLogEntry) -> None:
        """Discard *entry*; logging is disabled."""
        del entry


class NoopRelayUsageService(RelayUsageServiceProtocol):
    """Empty usage read service used when logging is disabled."""

    async def daily_usage(self, user_id: str, days: int) -> list[RelayDailyUsage]:
        """Return no usage for *user_id*."""
        del user_id, days
        return []

    async def model_rank(self, days: int, limit: int) -> list[RelayModelRank]:
        """Return no ranked models."""
        del days, limit
        return []


def register_relay_logs(
    container: ContainerRegistrarProtocol,
    config: object,
) -> None:
    """Register the relay request-log hierarchy by contract.

    The root always exposes ``RelayRequestLogStoreProtocol`` and
    ``RelayUsageServiceProtocol`` behind no-op instances so the gateway
    and admin surfaces can resolve the same protocol-shaped code path
    even when logging is disabled or the database is unavailable.  When
    logging is enabled, the durable store is built from the resolved
    database contract during :func:`boot_relay_logs` and the placeholders
    are rebound.

    Args:
        container: The container registrar to bind into.
        config: Governance configuration; ``enabled`` gates logging.
    """
    container.singleton(RelayRequestLogStoreProtocol, NoopRelayRequestLogStore())
    container.singleton(RelayUsageServiceProtocol, NoopRelayUsageService())
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_logs_disabled", reason="governance disabled")
        return
    logger.info("relay_logs_registered")


async def boot_relay_logs(
    container: BootContainerProtocol,
    config: object,
) -> None:
    """Build the relay log store and usage service and bind them by contract.

    Resolution is contract-scoped (only
    :class:`~lexigram.contracts.data.DatabaseProviderProtocol`).  When
    the database is missing, nothing is bound and a startup diagnostic
    is logged so the missing dependency is discoverable; the gateway
    keeps no-oping on the absent store.

    Args:
        container: The boot container used to resolve contracts.
        config: Governance configuration driving the bootstrap.
    """
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_logs_boot_skipped", reason="governance disabled")
        return

    database = await container.resolve_optional(DatabaseProviderProtocol)
    if database is None:
        logger.warning(
            "relay_logs_missing_dependency",
            missing="DatabaseProviderProtocol",
        )
        return

    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(database)
    service: RelayUsageServiceProtocol = RelayUsageService(database)
    container.bind(RelayRequestLogStoreProtocol, store)  # type: ignore[type-abstract]
    container.bind(RelayUsageServiceProtocol, service)  # type: ignore[type-abstract]
    logger.info("relay_logs_booted", store="SqlRelayRequestLogStore")
