"""Durable relay channel storage.

SQL-backed CRUD for relay channels behind the
``RelayChannelStoreProtocol`` contract, with revision compare-and-set
so stale writers never overwrite newer state.  Statically configured
channels remain the default; binding this store lets the gateway
reconcile its registry from durable rows at boot.

Exports:
    - ``SqlRelayChannelStore``: SQL-backed channel CRUD store.
"""

from lexigram.ai.governance.relay_channels.persistence import (
    SqlRelayChannelStore,
)

__all__ = ["SqlRelayChannelStore"]
