"""DI registrations and gateway hooks for durable relay channels.

The governance provider root keeps the channel store unbounded during
``register()`` (it needs a database that is only resolvable in
``boot()``).  :func:`boot_relay_channels` resolves the database through
its contract and binds ``RelayChannelStoreProtocol`` to the SQL store
so the gateway's boot reconcile and the admin CRUD actions resolve the
same instance through the container.  When no database is bound, the
protocol stays unbounded and the gateway keeps its static-configure
default behavior.

Nothing in this module imports gateway implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.governance import GovernanceConfig
from lexigram.ai.governance.relay_channels import SqlRelayChannelStore
from lexigram.contracts.ai.relay.store import RelayChannelStoreProtocol
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)

__all__ = ["boot_relay_channels", "register_relay_channels"]


def register_relay_channels(
    container: ContainerRegistrarProtocol,
    config: object,
) -> None:
    """Register durable relay channel services.

    Nothing is bound when governance is disabled.  The SQL store is
    built and bound during :func:`boot_relay_channels` once the
    database contract is resolvable; until then the gateway keeps its
    static channel configuration.

    Args:
        container: The container registrar to bind into.
        config: Governance configuration; ``enabled`` gates the store.
    """
    del container
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_channels_disabled", reason="governance disabled")
        return
    logger.info("relay_channels_registered")


async def boot_relay_channels(
    container: BootContainerProtocol,
    config: object,
) -> None:
    """Build the SQL channel store and bind it under its contract.

    Resolution is contract-scoped (only
    :class:`~lexigram.contracts.data.DatabaseProviderProtocol`).  When
    the database is missing, nothing is bound and a startup diagnostic
    is logged so the missing dependency is discoverable; the gateway
    keeps its static-configure default.

    Args:
        container: The boot container used to resolve contracts.
        config: Governance configuration driving the bootstrap.
    """
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_channels_boot_skipped", reason="governance disabled")
        return

    database = await container.resolve_optional(DatabaseProviderProtocol)
    if database is None:
        logger.warning(
            "relay_channels_missing_dependency",
            missing="DatabaseProviderProtocol",
        )
        return

    store = SqlRelayChannelStore(database)
    container.singleton(RelayChannelStoreProtocol, store)
    logger.info("relay_channels_booted", store="SqlRelayChannelStore")
