"""DI wiring for the governance relay ledger service.

Nothing is bound when governance is disabled.  The SQL ledger store
and service are built and bound during :func:`boot_relay_ledger` once
the database contract is resolvable.
"""

from __future__ import annotations

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.relay_ledger import (
    RelayLedgerService,
    SqlRelayLedgerStore,
)
from lexigram.contracts.ai.relay import RelayLedgerServiceProtocol
from lexigram.contracts.core.di import BootContainerProtocol
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["boot_relay_ledger", "register_relay_ledger"]


def register_relay_ledger(
    container: object,
    config: object,
) -> None:
    """Register relay ledger services.

    Args:
        container: The container registrar to bind into.
        config: Governance configuration; ``enabled`` gates the service.
    """
    del container
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_ledger_disabled", reason="governance disabled")
        return
    logger.info("relay_ledger_registered")


async def boot_relay_ledger(
    container: BootContainerProtocol,
    config: object,
) -> None:
    """Build the ledger store and service and bind the service contract.

    Args:
        container: The boot container used to resolve contracts.
        config: Governance configuration driving the bootstrap.
    """
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_ledger_boot_skipped", reason="governance disabled")
        return

    database = await container.resolve_optional(DatabaseProviderProtocol)
    if database is None:
        logger.warning(
            "relay_ledger_missing_dependency",
            missing="DatabaseProviderProtocol",
        )
        return

    store = SqlRelayLedgerStore(database)
    service = RelayLedgerService(store=store)
    container.singleton(RelayLedgerServiceProtocol, service)
    logger.info("relay_ledger_booted", store="SqlRelayLedgerStore")
