"""Durable channel reconciliation at gateway boot.

When a host binds a :class:`RelayChannelStoreProtocol`, the gateway
loads every durable row and merges it over the static configuration by
name: store rows override same-named static channels and store-only
channels are appended.  An empty store leaves the static table
byte-for-byte untouched, so the default configuration behavior is
preserved when no durable store is bound.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.relay.gateway import RelayChannel
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.ai.relay.store import RelayChannelStoreProtocol

logger = get_logger(__name__)

__all__ = ["DurableChannelLoader"]


class DurableChannelLoader:
    """Merge durable channel rows over a static channel table.

    Args:
        store: The durable store bound at boot; rows are read once.
    """

    def __init__(self, store: RelayChannelStoreProtocol) -> None:
        self._store = store

    async def load(self, static: tuple[RelayChannel, ...]) -> tuple[RelayChannel, ...]:
        """Return the static table merged with durable store rows.

        Store rows override same-named static channels; store-only
        channels keep the store order appended after the static
        channels.  An empty store returns *static* unchanged.

        Args:
            static: The configured channel table.

        Returns:
            The merged channel tuple, or *static* when the store is
            empty.

        Raises:
            ValueError: The store returned duplicate channel names.
        """
        rows = await self._store.list_channels()
        if not rows:
            return static
        durable: dict[str, RelayChannel] = {}
        for snap in rows:
            name = snap.channel.name
            if name in durable:
                raise ValueError(f"duplicate channel name from durable store: {name!r}")
            durable[name] = snap.channel
        merged = {ch.name: ch for ch in static}
        merged.update(durable)
        return tuple(merged.values())
